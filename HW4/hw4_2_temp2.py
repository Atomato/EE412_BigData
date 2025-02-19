import sys
from pyspark import SparkConf, SparkContext
import time

def dot(K, L):
	if len(K) != len(L):
		return 0
	return sum(i[0] * i[1] for i in zip(K, L))

conf = SparkConf()
sc = SparkContext(conf=conf)
sc.setLogLevel('WARN') # skip terminal log to see output well

# entire features
feat_e = sc.textFile(sys.argv[1]).map(lambda s: s.split(','))\
								.map(lambda l: list(map(float,l)))
feat_e = feat_e.collect()

lb_e = sc.textFile(sys.argv[2]).map(lambda l: float(l)) # entire labels
lb_e = lb_e.collect()

N_e = len(feat_e) # the number of data
dim = len(feat_e[0]) # features size
acc_test = []
for cv in range(10):
	test_n = N_e/10 # size of test chunk
	N = N_e - test_n # size of train chunks

	test_f = feat_e[(test_n*cv):(test_n*cv) + test_n] # test features
	test_l = lb_e[(test_n*cv):(test_n*cv) + test_n] # test labels

	# (feature i, label i)
	test = sc.parallelize(range(test_n)).map(lambda i: (test_f[i], test_l[i]))

	feat = feat_e[:]
	feat[(test_n*cv):(test_n*cv) + test_n] = [] # train features
	lb = lb_e[:]
	lb[(test_n*cv):(test_n*cv) + test_n] = [] # train labels	

	# (feature i, label i)
	train = sc.parallelize(range(N)).map(lambda i: (feat[i], lb[i]))

	w = [1./dim for _ in range(dim)]
	b = -1.

	c = 0.2 # penalty of misclassification
	lr = 0.0005 # learning rate eta	

	# train
	for k in range(50):
		cur_time = time.time()

		# (feature, label, y(dot(x,w)+b))
		margin = train.map(lambda (ft, lb): (ft, lb, lb*(dot(ft, w)+b)))
	
		# [gradients for w] + [gradient for b]
		gd = margin.filter(lambda (ft, lb, margin): margin < 1) \
			.map(lambda (ft, lb, margin): [-lb*ft[j] for j in range(dim)]+[-lb]) \
			.reduce(lambda gd0, gd1: [gd0[j] + gd1[j] for j in range(dim+1)])
		gd = [w[j] + c*gd[j] for j in range(dim)] + [c*gd[dim]]
		
		# update
		w = [w[j] - lr*gd[j] for j in range(dim)]
		b = b - lr*gd[dim]

		# print('iteration', k, '%.3f seconds'%(time.time()-cur_time))

	margin_test = test.map(lambda (ft, lb): lb*(dot(ft, w)+b))
	temp = margin_test.map(lambda margin: 1./test_n if margin>0 else 0.) \
					.reduce(lambda a, b: a+b)
	# print('%d fold test accuracy:'%cv, temp)
	acc_test.append(temp)

print(sum(acc_test)/10)
print(c)
print(lr)

# Result
# 0.834666666667
# 0.2
# 0.0005