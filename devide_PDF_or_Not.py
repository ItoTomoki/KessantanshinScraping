#encoding: UTF-8
import os
import MeCab
import urllib2
from bs4 import BeautifulSoup
from gensim import models
from gensim import corpora, matutils
from sklearn import svm, grid_search
from sklearn.cross_validation import KFold,StratifiedKFold
from sklearn import neighbors,svm,linear_model
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import numpy as np
from gensim import corpora 
from sklearn.model_selection import GridSearchCV
import re
import scipy
import argparse

positive_directory = os.listdir('positive_URL_set')
negative_directory = os.listdir('negative_data')

#ユーザー辞書を使う場合
#mecab = MeCab.Tagger('-Owakati -u ../userdictionary/hatena-keyword.dic, ../userdictionary/ruiter-keyword.dic, ../userdictionary/wikipedia-keyword.dic')
#ユーザー辞書を使わない場合
mecab = MeCab.Tagger('-Owakati')
text_information_dict = {}
for text in positive_directory:
	fname = 'positive_URL_set' + "/" + text
	html_text = open(fname).read()
	text_information = []
	soup = BeautifulSoup(html_text, "lxml")
	for a_tag in soup.find_all("a"):
		if a_tag.text != u"":
			text_information += mt.parse(a_tag.text.encode("utf-8")).split()
	text_information_dict[fname] = text_information

text_information_dict_neg = {}
for text in negative_directory:
	fname = 'negative_data/' + "/" + text
	html_text = open(fname).read()
	text_information = []
	soup = BeautifulSoup(html_text, "lxml")
	for a_tag in soup.find_all("a"):
		if a_tag.text != u"":
			#print a_tag.text
			#text_information.append(a_tag.text)
			text_information += mt.parse(a_tag.text.encode("utf-8")).split()
	text_information_dict_neg[fname] = text_information

dic = corpora.Dictionary(text_information_dict_neg.values() + text_information_dict.values())
dic.filter_extremes(no_below=5, no_above=0.3)
bow_corpus_neg = [dic.doc2bow(d) for d in text_information_dict_neg.values()]
bow_corpus_pos = [dic.doc2bow(d) for d in text_information_dict.values()]
BOW_vec_Mat_pos = matutils.corpus2csc(bow_corpus_pos, num_terms=len(dic)).tocsr().T
BOW_vec_Mat_neg = matutils.corpus2csc(bow_corpus_neg, num_terms=len(dic)).tocsr().T
# コストパラメータの設定（Grid Search用に複数設定）
cs = [0.001, 0.01, 0.1, 1, 10]
parameters = {'C': cs}
data_x = scipy.sparse.vstack([BOW_vec_Mat_pos[0:250], BOW_vec_Mat_neg[0:250]]).tocsr()
data_y = np.array([1] * 250 + [0] * 250)

def evaluate_data(data_Mat,target, clf = svm.LinearSVC(),use_grid = False):
	skf = StratifiedKFold(target, n_folds=5,shuffle = False)
	clf_list = []
	y_true_all = []
	y_pred_all = []
	for train_index, test_index in skf:
		X_train, X_test = data_Mat[np.array(train_index)], data_Mat[np.array(test_index)]
		y_train, y_test = target[np.array(train_index)], target[np.array(test_index)]
		if use_grid == True:
			clf = grid_search.GridSearchCV(svm.LinearSVC(),parameters,cv  =10)
		clf.fit(X_train, y_train)
		y_pred = clf.predict(X_test)
		y_true_all += list(y_test)
		y_pred_all += list(y_pred)
		print accuracy_score(y_test, y_pred)
		print classification_report(y_test,y_pred,digits = 4)
		print confusion_matrix(y_test,y_pred)
		clf_list.append(clf)
	return y_true_all, y_pred_all, clf_list

result = evaluate_data(data_x, data_y, use_grid = True)
print accuracy_score(result[0], result[1])

#URL_list(directory)一覧取得
fname = 'URLdirectoryList.txt'
directory_list = open(fname).read().split("\n")
directory_path_set = []

for path in directory_list:
	directory_path_set += re.split('[./]', path)

directory_path_set = set(directory_path_set)

def fild_all_files(directory):
    for root, dirs, files in os.walk(directory):
        yield root
        for file in files:
            yield os.path.join(root, file)

#分類器により該当ページかどうかを分類

def save_pdf_files(company_url, data_x, data_y, directory_path_set):
	os.system("wget -r -l 0 -e robots=off -A .php, .htm  --no-check-certificate " + company_url) 
	text_information_dict_new = {}
	#for file in fild_all_files('all_URL_data/www.bergearth.co.jp'):
	for file in fild_all_files(company_url):
		if ((".php" in file) | (".htm" in file)):
			print file
			html_text = open(file).read()
			text_information = []
			soup = BeautifulSoup(html_text)
			for a_tag in soup.find_all("a"):
				if a_tag.text != u"":
					text_information += mt.parse(a_tag.text.encode("utf-8")).split()
			text_information_dict_new[file] = text_information
	bow_corpus_new = [dic.doc2bow(d) for d in text_information_dict_new.values()]
	BOW_vec_Mat_new = matutils.corpus2csc(bow_corpus_new, num_terms=len(dic)).tocsr().T
	svc = svm.LinearSVC()
	clf = GridSearchCV(svc, parameters, cv = 10)
	clf.fit(data_x, data_y)
	y_pred_new = clf.predict(BOW_vec_Mat_new)
	url_select_svm_list = np.array(text_information_dict_new.keys())[y_pred_new == 1]
	add_URL_List_with_dir = []
	for URL in text_information_dict_new.keys():
		if len(set(URL.split("/")) & set(directory_path_set)) != 0:
			add_URL_List_with_dir.append(URL)
	url_select_list = [URL for URL in list(set(add_URL_List_with_dir + list(url_select_svm_list)))]
	URL = url_select_list[2]
	for URL in url_select_list:
		os.system("wget  -P " + str(company_url) + " -r -l 1 -e robots=off -A .pdf -nd --no-check-certificate " + str(URL))

def main():
	#ex: python devide_PDF_or_Not.py -URL www.bergearth.co.jp
	parser = argparse.ArgumentParser()
	parser.add_argument('-URL', type=str)
	args = parser.parse_args()
	save_pdf_files(args.URL, data_x, data_y, directory_path_set)

if __name__ == '__main__':
    main()