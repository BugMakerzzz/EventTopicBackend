from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

import re
import datetime
import codecs
import json

from WuhanBackend.models import Newsinfo, Viewsinfo
from WuhanBackend.SearchFunc import get_news_by_time, get_news_by_theme
from WuhanBackend.ClusterVps import k_means_tfidf


def foo(request):
    result = {'what':'foo'}
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

    # 数据返回封装
    result = {}
    result['newsList'] = [model_to_dict(news) for news in news_queryset]
    result['totalElements'] = len(result['newsList'])

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

    words = request.GET['kws'].strip()
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False

    # theme = '南海'
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

    result['totalElements'] = len(result['viewsList'])


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
    all_time = True
    all_keywords = True
    '''
    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')  
    if start_time != end_time:
        # print("start_time != end_time")
        all_time = False # 如果两者时间不同, 则有时间限制

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
    '''

    theme = '南海'
    words_list = '军事'
    all_keywords = False

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
    for news in news_queryset:
        # print(type(news.viewsinfo_set))
        newsid_set.add(news.newsid)
        time_str = news.time.strftime('%Y-%m-%d')
        if time_str in time_news_dict:
            time_news_dict[time_str].append(news)
        else:
            time_news_dict[time_str] = [news]
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


    tendency_data = {} # 用于事件分析页面的趋势数据
    timeline_data = {}  # 该时间范围内的时间-事件演化处理, 输出为json文件反馈给前端
    for time, newslist in time_news_dict.items():
        timeline_data[time] = []
        tendency_data[time] = len(newslist)
        
        title_list = [n.title for n in newslist]
        k_means_result = k_means_tfidf(title_list, 1, 5)
        
        for key in k_means_result[0].keys():
            tmp = {}
            tmp['cluster'] = str(key)
            tmp['center'] = k_means_result[1][key]

            if len(tmp['center']) < 10: # 过滤掉聚类效果不好的题目 
                continue

            tmp['title_list'] = []
            for i in k_means_result[0][key]:
                tmp['title_list'].append(title_list[i])
            timeline_data[time].append(tmp)

    # 事件预测模块处理
    eventpre_data = {
        "XXX": 24,
        "YYY": 36,
        "ZZZ": 56
    }

    # 数据返回封装
    result = {}
    result['tendency_data'] = tendency_data # 用于时间-趋势图
    result['eventpre_data'] = eventpre_data # 用于事件预测模块
    result['view_cluster_data'] = view_cluster_data # 用于观点聚类模块
    result['timeline_data'] = timeline_data # 用于时间轴数据处理


    with codecs.open("eventa_demo.json", "w", 'utf-8') as wf:
        json.dump(result, wf, indent=4)

    return JsonResponse({"foo":"title"})
