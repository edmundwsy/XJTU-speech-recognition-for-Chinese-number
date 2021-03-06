import data_loader as data_loader
import audio_processor
from utils import *
from sklearn.multiclass import OutputCodeClassifier
import numpy as np
import sklearn
import os
import time
from sklearn.ensemble import AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier

NUM = 10


class AudioClassification(object):
    def __init__(self, classifier, data_dir, save_path, num_clsfiers=20,
                 num_per_frame=100, if_loaded=False):

        self.N = NUM  # 类的数目
        self.M = num_clsfiers  # 分类器的数目
        self.method = classifier  # 使用分类器的代号

        # 导入数据
        if os.path.exists(os.path.join(save_path)) and if_loaded:
            data_base = np.load(os.path.join(save_path))
            print("Using saved data base")
        else:
            data_base = data_loader.data_loader(data_dir,
                                                num_per_frame=num_per_frame)
        # dataloader: list of numpy
        data_base = np.vstack(data_base)
        np.random.shuffle(data_base)
        data_base = np.hstack([data_base[:, :157], data_base[:, -1:]])
        print('\nNumber of Database: {}\n'.format(len(data_base)))
        # # 划分数据集
        # num_validation = int(0.1 * len(data_base))

        # # 由于都分到了6，因此去掉6看看分类器的效果
        # print("Before", len(data_base))
        # data_swap = []
        # for line in np.vsplit(data_base, len(data_base)):
        #     if line[:, -1] != 6:
        #         data_swap.append(line)
        # data_base = np.vstack(data_swap)
        # print("After", len(data_base))

        self.num_train_set = int(0.85 * len(data_base))
        num_test_set = int(0.90 * len(data_base))
        self.train_set = data_base[0:self.num_train_set]
        self.train_set_val = data_base[0: 50]  # 参与训练，就是看下分类器效果
        self.val_set = data_base[self.num_train_set:num_test_set]
        self.test_set = data_base[num_test_set:]

        # self.train_set = np.vstack([self.train_set, self.train_set, self.train_set, self.train_set, self.train_set])
        # np.random.shuffle(self.train_set)


        self.code_book = self.get_class_codebook()  # 码本
        self.clsfier_list = []
        self.accuracy_list = []
        self.accuracy = 0

    def _confusion_matrix(self, pred):
        '''
        生成 confusion matrix
        :param pred:
        :return:
        '''
        class_names = np.arange(10)
        plot_confusion_matrix(self.test_set[:, -1], pred,
                              classes=class_names, normalize=True,
                              title='Method: {} Accuracy: {}'.format(self.method, self.accuracy))

    def _get_predict_code(self, clf_list: list) -> list:

        predict_code = []
        if len(clf_list) < 1:
            clf_list = self.clsfier_list
            print("No input, using default")
        for cls in clf_list:  # 经过每个分类器，然后预测对应的类别，组成ECOC码
            pdct = cls.predict(self.test_set[:, :-1])
            predict_code.append(pdct)
        return predict_code

    def _find_code(self, input_data, positive, negative):
        '''
        找这个label对应的ECOC码
        :param input_data:
        :param positive:
        :param negative:
        :return:
        '''
        Y = np.zeros([input_data.shape[0], 1])
        for i in range(input_data.shape[0]):
            cls = input_data[i, -1].astype(np.int64)
            if cls in positive:
                Y[i] += 1
            elif cls in negative:
                Y[i] -= 1
            else:
                print('ERROR in code book')
                assert 0, 'ERROR in code book'
        return Y

    def _validate(self, classifier, X, Y):
        """
        使用验证集验证分类器的分类效果
        :param classifier:
        :param X:
        :param Y:
        :return:
        """
        predict = classifier.predict(X[:, :-1])
        error = np.abs(predict - Y.squeeze())
        accuracy = 1 - np.count_nonzero(error) / len(error)

        print("Validation: accuracy = {:.6f}".format(accuracy))
        return accuracy

    def _print_val(self, cls, if_cfmatrix=False):
        '''
        打印真实值、预测值和正确率
        :param cls:
        :param if_cfmatrix:
        :return:
        '''
        print('\n' + '-' * 20 + '\nMethod: \t', self.method)
        print("Predict:\n", cls)
        print("Ground Truth:\n", self.test_set[:, -1])
        result = (cls - self.test_set[:, -1]).astype(np.int64)
        print("Error\n", result)
        self.accuracy = 1 - np.count_nonzero(result) / len(result)
        print('-'*20 + '\n' + "ACCURACY: {:.6f}".format(self.accuracy) +
              '\n' + '-'*20 + '\n')
        if if_cfmatrix:
            self._confusion_matrix(cls)
        return result

    def get_class_codebook(self):
        '''
        获取ECOC码本
        :return:
        '''
        code_book = []
        for idx in range(self.M):
            code_line = np.ones(self.N).astype(np.int)
            y_label = np.arange(self.N)
            choice = np.random.choice(y_label, int(self.N // 2), replace=False)
            code_line[choice] *= -1
            code_book.append(code_line)
        code_book_np = np.vstack(code_book).transpose()
        print('\n' + '-' * 5 + 'CODEBOOK' + '-' * 5 + '\n')
        print(code_book_np.transpose())
        return code_book_np

    def _whats_wrong(self, predict, ground_truth, error):
        '''
        输出错误的分类结果，并排列
        :param predict:
        :param ground_truth:
        :param error:
        :return:
        '''
        index = np.nonzero(error)
        array = np.vstack([ground_truth, predict, error]).transpose()
        array = array[index]
        array = array[np.argsort(array, 0)[:, 0], :-1]
        print('\n' + '-' * 20 + '\n' + 'Error Display')
        print('gt' + '\t' + 'pd')
        # for i, eor in enumerate(error):
        #     if abs(eor) > 1e-5:
        #         print(predict[i], '\t-->\t\t', ground_truth[i])
        print(array)
        print('gt' + '\t' + 'pd')
        print(array[np.argsort(array, 0)[:, 1]])
        print('-' * 5)

    def train(self):
        if self.method in ['multi_dctree', 'svm_ovr', 'svm_ovo']:
            self.trainer_multi_classifier()
        elif self.method in ['lsvm', 'ksvm', 'dctree', 'sgd', 'bayes',
                                 'ada_boost', 'knn']:
            self.trainer_ecoc()
            AC.test(ifcfmatrix=True, if_show_error=False)

    def trainer_ecoc(self):

        for idx in range(self.M):
            ti = time.time()
            # get code
            positive_label = np.where(self.code_book[:, idx] > 0)[0]
            negative_label = np.where(self.code_book[:, idx] < 0)[0]
            Y = self._find_code(self.train_set, positive_label, negative_label)

            # train classifier
            clsfier = self.train_a_classifier(self.train_set[:, :-1], Y, num=1)
            self.clsfier_list.append(clsfier)
            print('\n' + '-'*5 + ' Trained classifier {} '.format(idx) + '-'*5)

            print("for training set:")
            _ = self._validate(clsfier, self.train_set[0:40, :], Y[0:40])

            # validate
            print("for validation set:")
            val = self._find_code(self.val_set, positive_label, negative_label)
            accuracy = self._validate(clsfier, self.val_set, val)
            self.accuracy_list.append(accuracy)  # 将每个分类器的准确率存起来
            tt = time.time()
            print('\t\ttime elapsed {:.2f} seconds'.format(tt - ti))

    def trainer_multi_classifier(self):
        """
        Without ECOC code book
        :return:
        """

        ti = time.time()

        # train classifier
        # self.clsfier = sklearn.svm.SVC()
        if self.method == 'svm_ovr':
            self.clsfier = sklearn.svm.SVC(decision_function_shape='ovr')
        elif self.method == 'svm_ovo':
            self.clsfier = sklearn.svm.SVC(decision_function_shape='ovo')
        elif self.method == 'multi_dctree':
            self.clsfier = sklearn.tree.DecisionTreeClassifier()
        else:
            self.clsfier = []
            Exception(' Undefined method !')
        self.clsfier.fit(self.train_set[:, :-1], self.train_set[:, -1])
        self.clsfier_list.append(self.clsfier)
        print('\n' + '-'*5 + ' Trained classifier {} '.format(0) + '-'*5)

        print("for training set:")
        _ = self._validate(self.clsfier, self.train_set[0:40, :],
                           self.train_set[0:40, -1])

        # validate
        print("for validation set:")
        accuracy = self._validate(self.clsfier,
                                  self.val_set,
                                  self.val_set[:, -1])
        self.accuracy_list.append(accuracy)  # 将每个分类器的准确率存起来
        tt = time.time()
        print('\t\ttime elapsed {:.2f} seconds'.format(tt - ti))

        self.test_multi_cls(self.test_set[:, :-1], self.test_set[:, -1])

    def trainer_reinforced(self, num_selected_classifiers):
        '''
        使用最优的几个分类器去分类，并测试效果
        Using best num_selected_classifiers to regenerate the model
        :return:
        '''
        # select best classifiers
        accuracy = np.array(self.accuracy_list).copy()
        best_clf_list = []
        best_label = np.zeros(num_selected_classifiers)
        for i in range(num_selected_classifiers):
            idx = np.where(accuracy.max() == accuracy)[0][0]
            best_clf_list.append(self.clsfier_list[idx])
            best_label[i] = idx
            accuracy[idx] = 0
        best_label = best_label.astype(np.int64)
        accuracy = np.hstack(self.accuracy_list)[best_label]
        print('' * 20 + '\n')
        print('Select {}'.format(np.vstack([best_label, accuracy])))

        codebook = self.code_book[:, best_label.astype(np.int64)]
        print(codebook)
        predict_code = self._get_predict_code(best_clf_list)
        predict_code = np.vstack(predict_code).transpose()
        cls = np.zeros(self.test_set.shape[0])
        for i, pdct in enumerate(predict_code):  # pdct: 1 * M
            dis = np.sum(np.abs(codebook - pdct) * accuracy, axis=1)
            cls[i] = np.argmin(dis)  # 每个分类器的准确率有不同的权重

        self._print_val(cls, if_cfmatrix=True)

    def train_a_classifier(self, data, label, num=1000):
        '''
        Should add other classifiers
        right now SVM only .
        :param data:
        :param label:
        :return:
        '''
        if self.method == 'lsvm':
            clf = sklearn.svm.LinearSVC()
        elif self.method == 'ksvm':
            clf = sklearn.svm.SVC(kernel='sigmoid', gamma='scale', max_iter=100000)
            # kernel: ‘linear’, ‘poly’, ‘rbf’, ‘sigmoid’, ‘precomputed’
            # gamma: 'auto' 'scale'
        elif self.method == 'dctree':
            clf = sklearn.tree.DecisionTreeClassifier()
        elif self.method == 'sgd':
            clf = sklearn.linear_model.SGDClassifier(
                loss="modified_huber", penalty="l2")
        elif self.method == 'bayes':
            clf = sklearn.naive_bayes.GaussianNB()
        elif self.method == 'ada_boost':
            clf = AdaBoostClassifier(n_estimators=100)
        elif self.method == 'knn':
            clf = KNeighborsClassifier()
        else:
            clf = []
            assert 0, "ERROR"

        for i in range(num):
            clf.fit(data, label.squeeze())
        return clf

    def test(self, ifcfmatrix=False, if_show_error=False):
        '''
        在测试集上测试分类效果
        :param ifcfmatrix: 是否需要输出 confusion matrix， 默认不输出
        :param if_show_error: 是否需要输出错误结果， 默认不输出
        :return:
        '''
        predict_code = []
        for idx in range(self.M):  # 经过每个分类器，然后预测对应的类别，组成ECOC码
            cls = self.clsfier_list[idx]
            pdct = cls.predict(self.test_set[:, :-1])
            predict_code.append(pdct)

        predict_code = np.vstack(predict_code).transpose()  # N * M
        accuracy = np.hstack(self.accuracy_list)  # TODO 不确定度？

        # give real code
        real_code = self.code_book.copy()
        cls = np.zeros(self.test_set.shape[0])
        for i, pdct in enumerate(predict_code):  # pdct: 1 * M
            dis = np.sum(np.abs(real_code - pdct) * accuracy, axis=1)
            cls[i] = np.argmin(dis)  # 每个分类器的准确率有不同的权重

        error = self._print_val(cls, if_cfmatrix=ifcfmatrix)
        if if_show_error:
            self._whats_wrong(cls, self.test_set[:, -1], error)

    def test_multi_cls(self, data, label):

        predict_code = self.clsfier.predict(data) # N * M
        # give real code
        print('\n' + '-' * 20 + '\nMethod: \t', self.method)
        print("Predict:\n", predict_code)
        print("Ground Truth:\n", label)
        print(len(predict_code))
        result = (predict_code - label).astype(np.int64)
        print("Error\n", result)
        self.accuracy = 1 - np.count_nonzero(result) / len(result)
        print('-'*20 + '\n' + "ACCURACY: {:.6f}".format(self.accuracy) +
              '\n' + '-'*20 + '\n')
        print('Confusion Matrix')
        self._confusion_matrix(predict_code)
        # print(sklearn.metrics.confusion_matrix(self.test_set[:, -1],
        #                                        predict_code))
        # self.whats_wrong(predict_code, label, result)


if __name__ == '__main__':
    np.random.seed(4)
    data_dir = "C:\\Users\\wsy\\Desktop\\dataset3"
    save_dir = "C:\\Users\\wsy\\Desktop\\dataset3\\mfccts128.npy"
    AC = AudioClassification('dctree', data_dir, save_dir,
                             num_clsfiers=40,
                             num_per_frame=128,
                             if_loaded=True)
    AC.train()
    # AC.trainer_reinforced(40)

# best at present:
# nc = 40, fl=0, fps=93
# upperate 64: 68  128: 69