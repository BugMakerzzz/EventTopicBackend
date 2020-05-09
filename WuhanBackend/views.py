from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

import re
import datetime
import codecs
import json
import pickle

from WuhanBackend.models import Newsinfo, Viewsinfo
from WuhanBackend.SearchFunc import get_news_by_time, get_news_by_theme
from WuhanBackend.ClusterVps import k_means_tfidf
from WuhanBackend.utils import clean_zh_text


def foo(request):
    result = {'what':'foo'}
    return JsonResponse(result)

# 主页面查询函数
def search_main(request):

    # 主页面只接收主题信息
    theme = request.GET['theme']   # 主题参数
    # theme = '南海'   # 主题参数
    # start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d') # 时间参数由前端决定
    # end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d') 
    start_time = datetime.datetime.strptime('2019-11-21', '%Y-%m-%d')
    end_time = datetime.datetime.strptime('2019-11-27', '%Y-%m-%d')
    delta_time = datetime.timedelta(days=1) # 用于时间轴的不连续问题 
    
    # 组合参数查询, 利用Q的多条件查询
    q = Q()
    q = q & Q(theme_label=theme)
    q = q & Q(time__range=(start_time, end_time))

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)
    
    # 综合选题框和专家观点框数据
    news_views_data = []
    time_news_dict = {} # 时间-新闻字典构建 {time:[自定义新闻tmp{}]}
    # 根据查询日期按天递增构建初始化字典
    nowtime = start_time
    while nowtime <= end_time:
        time_news_dict[nowtime.strftime('%Y-%m-%d')] = []
        nowtime += delta_time
    
    influence_max = 0   # 用于计算影响力指数的归一化   
    title_set = set() # 所选数据去重使用
    for n in news_queryset:
        
        title = clean_zh_text(n.title, 2)
        if title in title_set: continue # 如果title已经出现过, 则进行去重

        tmp = {}
        tmp['title'] = title
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer
        tmp['pos_sentiment'] = 0    # 根据新闻的评论计算正负向指数、影响力指数
        tmp['neg_sentiment'] = 0
        tmp['influence'] = 0
        tmp['content_label'] = n.content_label

        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n):
            tmp['views'].append(
                {
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer
                }
            )
            # 判断专家观点的情绪
            if v.sentiment > 0.6:
                tmp['pos_sentiment'] += 1
            else:
                tmp['neg_sentiment'] += 1
            tmp['influence'] += 1 # 有一个专家观点则增加一个新闻的影响力指数, 后续可以根据专家的权重来更改

        if len(tmp['views']) == 0: continue # 该新闻没有观点则略过

        # 对新闻的正负向指数进行归一化
        tmp['pos_sentiment'] = float(tmp['pos_sentiment'])/(tmp['pos_sentiment'] + tmp['neg_sentiment'])
        tmp['neg_sentiment'] = float(tmp['neg_sentiment'])/(tmp['pos_sentiment'] + tmp['neg_sentiment'])
        if tmp['influence'] > influence_max: # 记录影响力最大值, 便于后续对影响力数值进行归一化
            influence_max = tmp['influence']
        
        # 数据新增
        time_str = n.time.strftime('%Y-%m-%d')
        if time_str in time_news_dict:
            time_news_dict[time_str].append(tmp)
        else:
            print("search_main time_news_dict error: time_str not in start_time-end_time")

        title_set.add(title)
        news_views_data.append(tmp)

    # 三个统计图数据处理
    date_list = []
    hot_num = []
    sentiment_pos = []
    sentiment_neg = []
    influence_data = {} # {content_label:[n_data1, n_data2}
    
    for time, newslist in time_news_dict.items():
        date_list.append(time)
        # 热度趋势数据处理
        hot_num.append(len(newslist))
        # 正负向情感指数处理
        pos_num = 0
        neg_num = 0
        for n in newslist:
            pos_num += n['pos_sentiment']
            neg_num += n['neg_sentiment']

            # 右下角事件影响力处理
            n_data = [n['time'], float(n['influence'])/influence_max * 100, n['title']]
            
            influence_label = n['content_label'].split(' ')[0] # 此处仅显示新闻的第一个标签作为新闻分类
            
            if influence_label in influence_data:
                influence_data[influence_label].append(n_data)
            else:
                influence_data[influence_label] = [n_data]
        sentiment_pos.append(pos_num)
        sentiment_neg.append(neg_num)


    # 加载专题下国家-观点数量数据
    pkl_rf = open("WuhanBackend/dict/" + theme+ "_countryviews_dict.pkl",'rb')
    countryviews_dict = pickle.load(pkl_rf)
    max_views = 0
    mapdata_list = []
    for key, value in countryviews_dict.items():
        if value > max_views:
            max_views = value
        mapdata_list.append({"name":key, "value":value})

    # 结果封装
    result = {}
    result["news_views_data"] = news_views_data[:20] # 只返回处理的前20条数据
    result['map_data'] = {  # 地图数据
        "max": max_views,
        "min": 0,
        "data": mapdata_list
    }
    result['hot_data'] = {  # 下左数据
        'hot_date': date_list,
        'hot_num': hot_num
    }
    result['sentiment_data'] = {    #下中数据
        'sentiment_date': date_list,
        'sentiment_pos': sentiment_pos,
        'sentiment_neg': sentiment_neg
    }

    # 右下角气泡图数据封装
    legend_data = []
    series_data = []
    for key, value in influence_data.items():
        legend_data.append(key)
        series_data.append({
            'name': key,
            'type': 'scatter',
            'data': value
        })


    result['event_data'] = {
        "lengend": legend_data,
        "series": series_data
    }
    
    # return JsonResponse({"foo":"title"})
    return JsonResponse(result)


# 综合选题页面查询函数
@csrf_exempt    #关闭csrf保护功能
def search_xuanti(request):

    # 前端查询参数处理
    # all_theme = False
    # all_content = True
    all_time = True
    all_keywords = True

    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')  
    if start_time != end_time:
        print("start_time != end_time")
        all_time = False # 如果两者时间不同, 则有时间限制

    # language = request.GET['language']
    # print(language)
    # print(request.GET['kws_kinds'])
    # print(request.GET['include_text'])    # 是否搜索正文内容
    
    # 主题处理
    theme = request.GET['theme']   # 主题参数
    # print(theme)
    # print(request.GET['pageno'])
    pageno = int(request.GET['pageno']) # 当前页面编号
    pagesize = int(request.GET['size']) # 页面数据个数

    words = request.GET['kws'].strip()
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False

    # 组合参数查询, 利用Q的多条件查询
    q = Q()
    q = q & Q(theme_label=theme)

    '''
    if all_theme is False: # 具有主题限制
        # params['theme'] = theme_list
        q = q & Q(theme_label__in=theme_list)

    if all_content is False: # 具有事件标签限制
        # params['content_label'] = content_label_list
        q = q & Q(content_label__in=content_label_list)
    '''

    if all_time is False:   # 具有时间范围限制
        # params['start_time'] = start_time
        # params['end_time'] = end_time
        q = q & Q(time__range=(start_time, end_time))
    

    if all_keywords is False: # 具有关键词限制
        tmp_q = Q()
        for word in words_list:
            # tmp_q = tmp_q | Q(title__contains=word) # 关键词之间是'或'的关系, 使用该模式的话会由于前面的Q()而使其查询结果为全集
            tmp_q = tmp_q & Q(title__contains=word) # 关键词之间是'与'的关系
        q = q & tmp_q

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)
    totalElements = len(news_queryset)
    news_queryset = news_queryset[(pageno - 1) * pagesize: pageno * pagesize] # 根据前端分页进行切片处理

    # 数据返回封装
    result = {}
    result['newsList'] = [model_to_dict(news) for news in news_queryset]
    result['totalElements'] = totalElements

    '''
    # 将数据写入结果文件以便前端调试
    for news in result['newsList']:
        news['time'] = news['time'].strftime('%Y-%m-%d')
    
    with codecs.open("xuanti_demo.json", "w", 'utf-8') as wf:
        json.dump(result, wf, indent=4)
    '''
    return JsonResponse(result)

# 专家观点页面查询函数
def search_view(request):
    
    # 前端查询参数处理
    all_time = True
    all_keywords = True

    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')  
    if start_time != end_time:
        print("start_time != end_time")
        all_time = False # 如果两者时间不同, 则有时间限制
    
    # 主题处理
    theme = request.GET['theme']   # 主题参数

    pageno = int(request.GET['pageno']) # 当前页面编号
    pagesize = int(request.GET['size']) # 页面数据个数
    

    words = request.GET['kws'].strip()
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False
    
    # theme = '南海'
    # pageno = 1
    # pagesize = 64
    # words_list = '军事'
    # all_keywords = False

    # 组合参数查询, 利用Q的多条件查询
    # news_q = Q(theme_label=theme)
    # news_q = Q(newsid='3079863039838360687')

    view_q = Q(newsid__theme_label=theme) # 跨表查询符合条件的view, 正向关联

    if all_time is False:   # 具有时间范围限制
        view_q = view_q & Q(time__range=(start_time, end_time))
    

    if all_keywords is False: # 具有关键词限制
        tmp_q = Q()
        for word in words_list:
            # tmp_q = tmp_q | Q(viewpoint__contains=word) # 关键词之间是'或'的关系
            tmp_q = tmp_q & Q(viewpoint__contains=word) # 关键词之间是'与'的关系
        view_q = view_q & tmp_q

    # 查询语句
    views_queryset = Viewsinfo.objects.filter(view_q)
    totalElements = len(views_queryset)
    views_queryset = views_queryset[(pageno - 1) * pagesize: pageno * pagesize] # 根据前端分页进行切片处理


    # 数据返回封装
    result = {}
    result['viewsList'] = []
    for view in views_queryset:
        # 此时可以直接通过view.newsid来获取news的相关信息
        # if view.newsid.theme_label == theme:    # 两个条件的筛选并集
        # print(type(view.newsid))
        view_tmp = model_to_dict(view)
        view_tmp['time'] = view_tmp['time'].strftime('%Y-%m-%d') 
        view_tmp['newsinfo'] = {
            'title': view.newsid.title,
            'time': view.newsid.time.strftime('%Y-%m-%d'),
            'content': view.newsid.content,
            'theme': view.newsid.theme_label,
            'source': view.newsid.customer
        }
        # print(view_tmp)
        result['viewsList'].append(view_tmp)

    result['totalElements'] = totalElements


    # 将数据写入结果文件以便前端调试
    
    '''
    with codecs.open("view_demo.json", "w", 'utf-8') as wf:
        json.dump(result, wf, indent=4)
    '''

    # print(result['totalElements'])
    return JsonResponse(result)
    # return JsonResponse({"foo":"title"})


# 事件分析页面查询函数
def search_eventa(request):

    # 前端查询参数处理
    # all_theme = False
    # all_content = True
    all_time = False
    all_keywords = True
    
    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')  
    if start_time != end_time:
        # print("start_time != end_time")
        all_time = False # 如果两者时间不同, 则有时间限制
    else: # 两者时间相同, 给出默认时间
        start_time = datetime.datetime.strptime('2019-11-20', '%Y-%m-%d')
        end_time = datetime.datetime.strptime('2019-11-27', '%Y-%m-%d')

    # language = request.GET['language']
    # print(language)
    # print(request.GET['kws_kinds'])
    # print(request.GET['include_text'])    # 是否搜索正文内容
    
    # 主题处理
    theme = request.GET['theme']   # 主题参数
    # print(theme)
    # print(request.GET['pageno'])

    words = request.GET['kws'].strip()
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False
    

    # theme = '南海'
    # words_list = '军事'
    # start_time = datetime.datetime.strptime('2019-11-20', '%Y-%m-%d')
    # end_time = datetime.datetime.strptime('2019-11-27', '%Y-%m-%d')
    # all_keywords = False

    # 组合参数查询, 利用Q的多条件查询
    q = Q()
    q = q & Q(theme_label=theme)

    if all_time is False:   # 具有时间范围限制
        # params['start_time'] = start_time
        # params['end_time'] = end_time
        q = q & Q(time__range=(start_time, end_time))
    
    if all_keywords is False: # 具有关键词限制
        tmp_q = Q()
        for word in words_list:
            # tmp_q = tmp_q | Q(title__contains=word) # 关键词之间是'或'的关系, 使用该模式的话会由于前面的Q()而使其查询结果为全集
            tmp_q = tmp_q & Q(title__contains=word) # 关键词之间是'与'的关系
        q = q & tmp_q

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)
    # print(news_queryset.count())


    # 遍历新闻数据, 获取相关信息
    newsid_set = set()
    time_news_dict = {}
    # 根据查询日期按天递增构建初始化字典
    nowtime = start_time
    delta_time = datetime.timedelta(days=1) # 用于时间轴的不连续问题 
    while nowtime <= end_time:
        time_news_dict[nowtime.strftime('%Y-%m-%d')] = []
        nowtime += delta_time
    for n in news_queryset:
        # print(type(news.viewsinfo_set))
        newsid_set.add(n.newsid)
        time_str = n.time.strftime('%Y-%m-%d')
        if time_str in time_news_dict:
            time_news_dict[time_str].append(n)
        else:
            print("search_eventa time_news_dict error: time_str not in start_time-end_time")
    # print(time_news_dict)

    # 根据newsid查询观点
    view_queryset = Viewsinfo.objects.filter(newsid__in=newsid_set)
    # print(view_queryset.count())
    
    # 构建观点聚类结果
    view_set = set()
    for view in view_queryset:
        # print(view.viewpoint)
        # print(view.newsid)
        # print(view.viewid)
        view_set.add(view.viewpoint)

    view_list = list(view_set)
    if len(view_list) == 0:
        print("search_eventa error: view_list size is 0.")

    view_cluster_data = []
    view_cluster_result = k_means_tfidf(view_list, 5, 10)
    for key in view_cluster_result[0].keys():
        view_tmp = {}
        view_tmp['cluster'] = str(key)
        view_tmp['center'] = view_cluster_result[1][key]

        if len(view_tmp['center']) < 10: # 过滤掉聚类效果不好的观点 
            continue

        view_tmp['view_num'] = len(view_cluster_result[0][key])
        view_tmp['view_list'] = [view_list[i] for i in view_cluster_result[0][key]]
        view_cluster_data.append(view_tmp)


    tendency_time = [] # 用于事件分析页面的趋势数据
    tendency_news = []
    
    timeline_news = [] # 时间轴的新闻数据列表
    for time, newslist in time_news_dict.items():
        # 趋势图数据处理
        tendency_time.append(time)
        if len(newslist) == 0:  # 当天没有检索到新闻的情况
            tendency_news.append({
                'name': 'None',
                'value': 0
            })
        else:
            title_tmp = newslist[0].title # 每天的关键事件筛选
            tendency_news.append({
                'name': title_tmp,
                'value': len(newslist)
            })
        
        # 时间-新闻轴数据处理
        title_list = []
        title_news_dict = {}
        for n in newslist:
            if n.title not in title_news_dict:
                title_list.append(n.title)
                title_news_dict[n.title] = n

        if len(title_list) < 3: # 当天新闻数量小于3则不进行聚类, 直接给出
            for t in title_list:
                t_new = title_news_dict[t]
                tmp = {}
                tmp['id'] = t_new.newsid
                tmp['title'] = t_new.title
                tmp['content'] = t_new.content
                tmp['url'] =  t_new.url
                tmp['foreign'] = False
                tmp['dateDay'] = time
                # 将数据增添进列表中
                timeline_news.append(tmp)
        else:
            k_means_result = k_means_tfidf(title_list, 1, 3) # 新闻数量超过三则进行聚类
            for key in k_means_result[0].keys():
                t = k_means_result[1][key] # 聚类中心的title
                
                if len(t) < 10: # 过滤掉聚类效果不好的题目 
                    continue
                
                t_new = title_news_dict[t]
                tmp = {}
                tmp['id'] = t_new.newsid
                tmp['title'] = t_new.title
                tmp['content'] = t_new.content
                tmp['url'] =  t_new.url
                tmp['foreign'] = False
                tmp['dateDay'] = time
                # 将数据增添进列表中
                timeline_news.append(tmp)

                '''
                tmp['title_list'] = []
                for i in k_means_result[0][key]:
                    tmp['title_list'].append(title_list[i])
                '''

    # 趋势轴数据
    tendency_data = {
        "tendency_time": tendency_time,
        "tendency_news": tendency_news
    }

    # 时间-事件轴数据
    timeline_data = {
        "data": timeline_news
    }

    # 事件预测模块处理
    nextevent_des_list = ['XXX','YYY','ZZZ']
    nextevent_exp_list = [24, 25, 36]
    eventpre_data = {
        'legend_data': nextevent_des_list,
        'data': [{'name': x, 'value': y} for x, y in zip(nextevent_des_list, nextevent_exp_list)]
    }

    # 数据返回封装
    result = {}
    result['tendency_data'] = tendency_data # 用于时间-趋势图
    result['eventpre_data'] = eventpre_data # 用于事件预测模块
    result['view_cluster_data'] = view_cluster_data # 用于观点聚类模块
    result['timeline_data'] = timeline_data # 用于时间轴数据处理

    
    with codecs.open("eventa_demo.json", "w", 'utf-8') as wf:
        json.dump(result, wf, indent=4)
    
    # return JsonResponse({"foo":"title"})
    return JsonResponse(result)