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
def search_xuanti_news(request):

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
    print(theme)
    print(request.GET['pageno'])

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
        # params['keywords'] = words_list
        # q = q & Q()
        tmp_q = Q()
        for word in words_list:
            tmp_q = tmp_q | Q(title__contains=word) # 关键词之间是'或'的关系
            # tmp_q = tmp_q & Q(title__contains=word) # 关键词之间是'与'的关系
        q = q & tmp_q

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)

    # 数据返回封装
    result = {}
    result['newsList'] = [model_to_dict(news) for news in news_queryset]
    result['totalElements'] = len(result['newsList'])
    return JsonResponse(result)


# 事件分析页面查询函数
def search_eventdeal(request):
    '''
    请求样式:
    request.GET = {'year_from': 2010, 'month_from': 1, 'day_from': 1,
               'year_to':2013, 'month_to': 10, 'day_to': 1}
    '''
    '''
    从request中获取start_time和 end_time
    if 'year_from' and 'month_from' and 'day_from' and\
            'year_to' and 'month_to' and 'day_to' in request.GET:
        y = request.GET['year_from']
        m = request.GET['month_from']
        d = request.GET['day_from']
        date_from = datetime.datetime(int(y), int(m), int(d), 0, 0)
        y = request.GET['year_to']
        m = request.GET['month_to']
        d = request.GET['day_to']
        date_to = datetime.datetime(int(y), int(m), int(d), 0, 0)
    else:
        print "error time range!"
    '''

    # 前端查询参数处理
    all_theme = False
    all_content = True
    all_time = False
    all_keywords = False

    start_time = datetime.datetime(2019, 8, 2, 0, 0)    # 对应前端的时间范围筛选框
    end_time = datetime.datetime(2019, 9, 2, 0, 0)
    
    theme_list = ['南海']   # 对应前端的主题筛选标签
    content_label_list = ['入侵行动','防卫行动'] # 对应前端的事件筛选标签
    
    words_list = ['南海', '军事'] # 对应前端的查询框
    

    # 单一参数查询
    # news_queryset = get_news_by_time(start_time, end_time)
    # news_queryset = get_news_by_theme(theme_list)

    # 组合参数查询, 利用Q的多条件查询
    # params = {}
    q = Q()
    
    if all_theme is False: # 具有主题限制
        q = q & Q(theme_label__in=theme_list)

    if all_content is False: # 具有事件标签限制
        q = q & Q(content_label__in=content_label_list)

    if all_time is False:   # 具有时间范围限制
        q = q & Q(time__range=(start_time, end_time))
    

    if all_keywords is False: # 具有关键词限制
        q = q & Q()
        tmp_q = Q()
        for word in words_list:
            # tmp_q = tmp_q | Q(title__contains=word)
            tmp_q = tmp_q & Q(title__contains=word) # 关键词查询的并集
        q = q & tmp_q

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)

    # 该时间范围内的时间-事件演化处理
    timeline_data = {}  # 输出为json文件反馈给前端
    time_news_dict = {}
    for news in news_queryset:
        time_str = news.time.strftime('%Y-%m-%d')
        if time_str in time_news_dict:
            time_news_dict[time_str].append(news)
        else:
            time_news_dict[time_str] = [news]
    # print(time_news_dict)
    # 进行k_means聚类构建时间线
    for time, newslist in time_news_dict.items():
        timeline_data[time] = []
        
        title_list = [n.title for n in newslist]
        k_means_result = k_means_tfidf(title_list, 1, 5)
        
        for key in k_means_result[0].keys():
            tmp = {}
            tmp['cluster'] = str(key)
            tmp['center'] = k_means_result[1][key]
            tmp['title_list'] = []
            for i in k_means_result[0][key]:
                tmp['title_list'].append(title_list[i])
            timeline_data[time].append(tmp)

    # 数据返回封装
    result = {}
    result['start_time'] = start_time
    result['end_time'] = end_time
    result['timeline_data'] = timeline_data
    result['news_list'] = [model_to_dict(news) for news in news_queryset]
    return JsonResponse(result)