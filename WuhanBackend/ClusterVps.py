#聚合所有新华社的用户群体观点
#取出所有新闻的ID
import csv
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn import metrics
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer
from sklearn import preprocessing
import numpy as np
from gensim.models.word2vec import Word2Vec
from gensim import corpora
from gensim.models import lsimodel, ldamodel, tfidfmodel
import jieba
import json
def select_best_k(models, x):
    best_k = list(models.keys())[0]
    max_silhouette = -10000
    for k in list(models.keys()):
        labels = models[k].labels_
        try:
            silhouette = metrics.silhouette_score(x, labels, metric='euclidean')
            print(k, silhouette)
            if silhouette > max_silhouette:
                best_k = k
                max_silhouette = silhouette
        except Exception as e:
            print(e)
    if best_k <= 2:
        if best_k + 1 in models:                       # 至少两个类
            best_k += 1
    return best_k

def vec_dis(v1,v2):
    v=v1-v2
    v=np.abs(v)
    v=np.sum(v)
    return v


# 对照cluster_tool.py中的实现将jieba分词内置其中, 即corpus传参为分词前的句子列表
def k_means_tfidf(corpus, min_num, max_num):
    #docs=corpus
    docs=[]
    for doc in corpus:
        words=jieba.lcut(doc)
        ndoc=words[0]
        for j in range(len(words)):
            ndoc=ndoc+" "+words[j]
        docs.append(ndoc)

    #docs = [" ".join(doc) for doc in corpus]
    vectorizer = CountVectorizer()
    transformer = TfidfTransformer()
    tfidf = transformer.fit_transform(vectorizer.fit_transform(docs))
    weight = tfidf.toarray()
    #计算中心
    if len(corpus) > 2:
        models = {}
        num_topics_min = min(min_num, len(corpus) - 1)
        num_topics_max = min(max_num, len(corpus))
        # num_topics_max = min(len(corpus)// 10, len(corpus))
        step = max(2, (num_topics_max - num_topics_min) // 8)
        for k in range(num_topics_min, num_topics_max, step):
            # models[k] = KMeans(n_clusters=k).fit(weight)
            models[k] = AgglomerativeClustering(n_clusters=k).fit(weight)

        # select best k
        if len(corpus) > 2:
            bst_k = select_best_k(models, weight)
        else:
            bst_k = list(models.keys())[0]

        topics = {topic: [] for topic in range(bst_k)}
        for i, topic_no in enumerate(models[bst_k].labels_):
            topics[topic_no].append(i)
        #计算中心
        topics_2_sentences={}
        for topic in topics:
            idxs=topics[topic]

            vec=weight[idxs]
            #算出中心和那个是最接近的
            center=np.mean(vec,0)
            dis=[]
            for v in vec:
                dis.append(vec_dis(v,center))
            center=idxs[np.argmin(dis)]
            topics_2_sentences[topic]=corpus[center]
            #print(center)
        return topics,topics_2_sentences
    else:
        topics_2_sentences={0:corpus[0]}
        topics={0: [i for i in range(len(corpus))]}
        return topics,topics_2_sentences

def extract_cluster_user_vps():
    #
    news_ids = []
    fin = "20191122.csv"
    data = pd.read_csv(fin)
    for j in range(1, data.shape[0]):
        key = data.loc[j]
        news_ids.append(key['news_id'])
    # print(news_ids)
    postuser_2_news = {}
    fin = "新闻列表.csv"
    data = pd.read_csv(fin)
    user_vps=[]
    for j in range(1, data.shape[0]):
        key = data.loc[j]
        news_id = key['news_id']
        time = key['time']
        if news_id not in news_ids:
            # print(news_id,time)
            continue
        comments=str(key['comments'])
        if comments=='nan':
            continue
        #print(comments)
        if len(comments)==0:
            continue
        comments=json.loads(comments)
        '''
        [{"against":0,"agreeCount":1,"ip":"117.84.8.*","nickname":"海之声宜兴中心","pubTime":1542518470,"replyId":"1237914235","replycontent":"[微笑]","sex":9,"sourceId":4,"uId":79226769}]
        '''
        for comment in comments:
            reply_content=comment['replycontent']
            if len(reply_content)<10:
                continue
            info={}
            info['reply_content']=reply_content
            info['news_id']=news_id
            info['nickname']=comment['nickname']
            user_vps.append(info)
    vps_all=[info['reply_content'] for info in user_vps]
    vps_all_cluster=k_means_tfidf(vps_all,1,10)
    print(vps_all_cluster[0])
    print(vps_all_cluster[1])
    print(len(user_vps))
    # 阅读观点
    json_data={}
    json_data['viewpoints']=user_vps
    json_data['cluster_result']=vps_all_cluster[0]
    json_data['cluster_result_center'] = vps_all_cluster[1]
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return super(NpEncoder, self).default(obj)
    json_str = json.dumps(json_data, ensure_ascii=False, indent=4, cls=NpEncoder)
    with open('用户观点_20191122.json', 'w', encoding='utf-8') as json_file:
        json_file.write(json_str)
    print(postuser_2_news)

#抽取标题关键词，然后根据标题关键词匹配标题
def extract_sentences(sentences):
    words=[]
    words_sentence=[]
    for sentence in sentences:
        words_t=jieba.lcut(sentence)
        words=words+words_t
        words_sentence.append(words)
    words_num={}
    for word in words:
        words_num[word]=0
    for word in words_num:
        words_num[word]=words_num[word]+1
    v=np.zeros([len(sentences)])
    for i in range(len(sentences)):
        for word in words_sentence[i]:
            v[i]=v[i]+words_num[word]
    return sentences[np.argmax(v)]

def extract_cluster_meiti_vps():
    #
    news_ids=[]
    fin = "20191122.csv"
    data = pd.read_csv(fin)
    for j in range(1,data.shape[0]):
        key=data.loc[j]
        news_ids.append(key['news_id'])
    #print(news_ids)
    postuser_2_news={}
    fin="新闻列表.csv"
    data = pd.read_csv(fin)
    for j in range(1,data.shape[0]):
        key=data.loc[j]
        news_id=key['news_id']
        time=key['time']
        if news_id not in news_ids:
            #print(news_id,time)
            continue
        customer=key['customer']
        if customer not in postuser_2_news:
            postuser_2_news[customer]=[]
        postuser_2_news[customer].append(key['news_id'])
    #阅读观点
    news_id_2_vps={}
    #这里要读入所有的观点
    fin = "南海自由航行_views.csv"
    data = pd.read_csv(fin)
    for j in range(1, data.shape[0]):
        key = data.loc[j]
        #person_name,org_name,pos,verb,viewpoint,person_id,org_id,news_id,sentiment,time,publish_time,original_text
        news_id=key['news_id']
        viewpoint=key['viewpoint']
        if news_id not in news_ids:
            continue
        if news_id not in news_id_2_vps:
            news_id_2_vps[news_id]=[]
        news_id_2_vps[news_id].append(viewpoint)
    json_data={}
    for post_user in postuser_2_news:
        if len(postuser_2_news[post_user])>0:
            print(post_user)
            vps_all=[]
            vps_news_all=[]
            for news_id in postuser_2_news[post_user]:
                if news_id not in news_id_2_vps:
                    continue
                vps=news_id_2_vps[news_id]
                for vp in vps:
                    vps_all.append(vp)
                    vps_news_all.append(news_id)

            print(vps_all)
            if len(vps_all)<1:
                continue
            vp_cluster=k_means_tfidf(vps_all,1,5)
            info={}
            info['viewpoints']=vps_all
            info['viewpoints_newsid']=vps_news_all
            info['cluster_result']=vp_cluster[0]
            info['clutser_result_center']=vp_cluster[1]
            json_data[post_user]=info
            print(vp_cluster)
            print()
                #只分析11月22日前后一周的新闻观点

    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return super(NpEncoder, self).default(obj)

    json_str = json.dumps(json_data,ensure_ascii=False,indent=4,cls=NpEncoder)
    with open('媒体观点_20191122.json', 'w',encoding='utf-8') as json_file:
        json_file.write(json_str)
    print(postuser_2_news)



if __name__ == '__main__':
    corpus = ["我 来到 北京 清华大学",  # 第一类文本切词后的结果，词之间以空格隔开
              "他 来到 了 网易 杭研 大厦",  # 第二类文本的切词结果
              "小明 硕士 毕业 与 中国 科学院",  # 第三类文本的切词结果
              "我 爱 北京 天安门"]
    r = extract_cluster_user_vps()
