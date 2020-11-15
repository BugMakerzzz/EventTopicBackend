from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

import re
import datetime
import codecs
import json
import pickle
import os
import time
from fuzzywuzzy import fuzz

from WuhanBackend.settings import BASE_DIR

from WuhanBackend.models import Newsinfo, Viewsinfo, Othernewsinfo
from WuhanBackend.SearchFunc import get_news_by_time, get_news_by_theme
from WuhanBackend.ClusterVps import k_means_tfidf


def foo(request):
    result = {'what':'foo'}
    return JsonResponse(result)

# 缓存信息清除函数
def clear_cathe(request):
    result = {'clear_cathe':'success'}
    cache_file_dir = os.path.join(BASE_DIR, "WuhanBackend/cache/")
    if os.path.exists(cache_file_dir):   # 缓存文件夹存在, 清除缓存信息
        cache_files = os.listdir(cache_file_dir)
        for f in cache_files:
            # print(os.path.join("WuhanBackend/cache/", f))
            os.remove(os.path.join(cache_file_dir, f))
    return JsonResponse(result)

# 主页面的新闻筛选展示算法, 用于二级界面缓存文件不存在时的冷启动
def main_news_show(theme):
    q = Q(theme_label=theme)
    # 主页面数据展示(用于左上角、右上角以及右下角的数据处理)
    start_time = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d') # 主页面时间范围, 2020年以来的数据
    show_queryset = Newsinfo.objects.filter(q & Q(time__gte=start_time))
    time_queryset = show_queryset.order_by('-time')
    crisis_queryset = show_queryset.order_by('-crisis')
    COVID_queryset = Newsinfo.objects.filter(q & (Q(title__contains='新冠') | Q(title__contains='病毒') | Q(title__contains='疫情') | Q(title__contains='肺炎')))
    
    show_news_date_list = []
    
    # 每种条件筛选20条
    title_set = set()
    show_size = 20  # 每种逻辑的show_size
    start = time.time() # 计算主页面的逻辑处理时间

    # 根据日期筛选
    count = 0
    for n in time_queryset: # 根据日期筛选
        
        title = n.title
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        if n.influence == 0: continue # 如果当前新闻没有专家观点则滤掉
        if n.crisis <= 0: continue # 如果当前新闻没有风险度则过滤掉
        tmp = {}
        tmp['title'] = title
        tmp['newsid'] = n.newsid
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer

        
        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n):
            # 筛选效果较好的观点
            if len(v.viewpoint) < 10: continue
            if v.country == '': continue
            tmp['views'].append(
                {
                    'viewid': v.viewid,
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer,
                    'time': v.time
                }
            )
       
        if len(tmp['views']) == 0: continue        
        show_news_date_list.append(tmp)
        title_set.add(n.title)
        count += 1
        if count >= show_size: break 
    
    # 根据危机指数筛选
    count = 0
    for n in crisis_queryset: # 根据危机指数筛选
        title = n.title
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        if n.influence == 0: continue # 如果当前新闻没有专家观点则滤掉
        tmp = {}
        tmp['title'] = title
        tmp['newsid'] = n.newsid
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer
        
        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n.newsid):
            # 筛选效果较好的观点
            if len(v.viewpoint) < 10: continue
            if v.country == '': continue
            tmp['views'].append(
                {
                    'viewid': v.viewid,
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer,
                    'time': v.time
                }
            )

        if len(tmp['views']) == 0: continue
        show_news_date_list.append(tmp)
        title_set.add(n.title)
        count += 1
        if count >= show_size: break 

    # 根据疫情相关新闻筛选 
    count = 0
    for n in COVID_queryset: # 根据疫情相关新闻筛选
        title = n.title
        # print(title)
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        if n.influence == 0: continue # 如果当前新闻没有专家观点则滤掉
        tmp = {}
        tmp['title'] = title
        tmp['newsid'] = n.newsid
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer
        
        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n.newsid):
            # 筛选效果较好的观点
            if len(v.viewpoint) < 10: continue
            if v.country == '': continue
            tmp['views'].append(
                {
                    'viewid': v.viewid,
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer,
                    'time': v.time
                }
            )
        
        if len(tmp['views']) == 0: continue
        show_news_date_list.append(tmp)
        title_set.add(n.title)
        count += 1
        if count >= show_size: break

    return show_news_date_list 

# 主页面查询函数
def search_main(request):

    SHOW_NEWS_NUM = 30 # 显示的新闻个数
    # 主页面只接收主题信息
    theme = request.GET['theme']   # 主题参数
    # theme = '南海'   # 主题参数
    cathe_flag = True # 是否使用cache


    # 根据theme检查缓存
    search_key = theme + "_mainpage"
    cache_file_dir = os.path.join(BASE_DIR, "WuhanBackend/cache/")
    cache_file_name = os.path.join(BASE_DIR, "WuhanBackend/cache/" + search_key + ".pkl")
    if not os.path.exists(cache_file_dir):   # 文件夹不存在则创建文件夹
        os.mkdir(cache_file_dir)
    if cathe_flag and os.path.exists(cache_file_name): # 缓存已经存在
        pkl_rf = open(cache_file_name,'rb')
        result = pickle.load(pkl_rf)
        return JsonResponse(result)
    
    # 组合参数查询, 利用Q的多条件查询
    q = Q()
    q = q & Q(theme_label=theme)

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q)


    # 左下,右下 统计图数据处理
    time_count_dict = {}
    for n in news_queryset:
        time_str = n.time.strftime('%Y-%m') # 按照月份进行处理
        tmp = {}
        if time_str in time_count_dict:
            time_count_dict[time_str]['news_count'] += 1
            time_count_dict[time_str]['pos_sentiment'] += n.positive
            time_count_dict[time_str]['neg_sentiment'] += n.negative
        else:
            tmp['news_count'] = 1
            tmp['pos_sentiment'] = n.positive
            tmp['neg_sentiment'] = n.negative
            time_count_dict[time_str] = tmp
    
    date_list = []
    hot_num = []
    sentiment_pos = []
    sentiment_neg = []
    sorted_data = []
    
    for t, data in time_count_dict.items():
        sorted_data.append((datetime.datetime.strptime(t, '%Y-%m'), data['news_count'], float("%.2f" % data['pos_sentiment']), float("%.2f" % data['neg_sentiment'])))

    sorted_data = sorted(sorted_data, key=lambda x: x[0]) # 根据时间进行升序排序

    for data in sorted_data:
        date_list.append(data[0])
        hot_num.append(data[1])
        sentiment_pos.append(data[2])
        sentiment_neg.append(data[3])
    
   
    # 主页面数据展示(用于左上角、右上角以及右下角的数据处理)
    start_time = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d') # 主页面时间范围, 2020年以来的数据
    show_queryset = Newsinfo.objects.filter(q & Q(time__gte=start_time))
    time_queryset = show_queryset.order_by('-time')
    crisis_queryset = show_queryset.order_by('-crisis')
    reliability_queryset = show_queryset.order_by('-reliability')
    # COVID_queryset = Newsinfo.objects.filter(q & (Q(title__contains='新冠') | Q(title__contains='病毒') | Q(title__contains='疫情') | Q(title__contains='肺炎')))
    
    show_news_date_list = [] # 根据时间筛选的新闻
    show_news_crisis_list = [] # 根据风险度筛选的新闻
    
    # 每种条件筛选10条
    title_set = set()
    show_size = 30  # 每种逻辑的show_size
    start = time.time() # 计算主页面的逻辑处理时间
    
    # 根据日期筛选
    count = 0
    for n in time_queryset: # 根据日期筛选
        
        title = n.title
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        if n.influence == 0: continue # 如果当前新闻没有专家观点则滤掉
        if n.crisis <= 0: continue # 如果当前新闻没有风险度则过滤掉
        tmp = {}
        tmp['title'] = title
        tmp['newsid'] = n.newsid
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer
        
        tmp['crisis'] = n.crisis
        tmp['nextevent'] = n.nextevent.split(',')[0].split(':')[0]
        tmp['content_label'] = n.content_label.split(' ')

        view_set = set() # 用于观点去重
        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n):
            # 筛选效果较好的观点
            if v.viewpoint in view_set: continue
            if len(v.viewpoint) < 10: continue
            if v.country == '': continue
            tmp['views'].append(
                {
                    'viewid': v.viewid,
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer,
                    'time': v.time
                }
            )
            view_set.add(v.viewpoint)
       
        if len(tmp['views']) == 0: continue        
        show_news_date_list.append(tmp)
        title_set.add(n.title)
        count += 1
        if count >= show_size: break 
    
    # 根据危机指数筛选
    count = 0
    for n in crisis_queryset: # 根据危机指数筛选
        title = n.title
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        if n.influence == 0: continue # 如果当前新闻没有专家观点则滤掉
        tmp = {}
        tmp['title'] = title.replace("原创",'').replace("转帖",'').replace("参考消息",'') # 过滤title信息
        tmp['newsid'] = n.newsid
        tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
        tmp['views'] = []
        tmp['source'] = n.customer

        tmp['crisis'] = n.crisis
        tmp['nextevent'] = n.nextevent.split(',')[0].split(':')[0]
        tmp['content_label'] = n.content_label.split(' ')
        
        view_set = set() # 用于观点去重
        # 遍历新闻的观点然后进行处理, 每次filter都会访问一次数据库
        for v in Viewsinfo.objects.filter(newsid=n.newsid):
            # 筛选效果较好的观点
            if v.viewpoint in view_set: continue
            if len(v.viewpoint) < 10: continue
            if v.country == '': continue
            tmp['views'].append(
                {
                    'viewid': v.viewid,
                    'personname': v.personname,
                    'orgname': v.orgname,
                    'pos': v.pos,
                    'verb': v.verb,
                    'viewpoint': v.viewpoint,
                    'country': v.country,
                    'source': n.customer,
                    'time': v.time
                }
            )
            view_set.add(v.viewpoint)

        if len(tmp['views']) == 0: continue
        show_news_crisis_list.append(tmp)
        title_set.add(n.title)
        count += 1
        if count >= show_size: break 
 
    # 选取crisis前100的数据进行右下角的危机事件展示
    count = 0
    title_set = set()
    crisis_data = {} # {content_label:[n_data1, n_data2} 
    for n in reliability_queryset: # 根据可靠性选取100条可靠性高的新闻
        # 右下角事件危机指数处理
        title = n.title.replace("原创",'').replace("转帖",'').replace("参考消息",'')
        if title in title_set: continue # 如果title已经出现过, 则进行去重
        crisis_value = n.crisis
        if crisis_value < 1: continue # 选取具有风险度的新闻
        n_data = [n.time.strftime('%Y-%m-%d %H:%M:%S'), crisis_value, title]
        crisis_label = n.content_label.split(' ')[0] # 此处仅显示新闻的第一个标签作为新闻分类
            
        if crisis_label in crisis_data:
            crisis_data[crisis_label].append(n_data)
        else:
            crisis_data[crisis_label] = [n_data]
        
        title_set.add(title)
        count += 1
        if count >= 100: break 

    # 加载专题下国家-观点数量数据
    pkl_rf = open(os.path.join(BASE_DIR,"WuhanBackend/dict/echarts_zhcountry_set.pkl"),'rb')
    zhcountry_set = pickle.load(pkl_rf)
    pkl_rf = open(os.path.join(BASE_DIR,"WuhanBackend/dict/" + theme+ "_countryviews_dict.pkl"),'rb')
    countryviews_dict = pickle.load(pkl_rf)
    # 补全全部国家信息
    for i in zhcountry_set: 
        if i not in countryviews_dict:
            countryviews_dict[i] = 0
    max_views = 0
    mapdata_list = []
    for key, value in countryviews_dict.items():
        if value > max_views:
            max_views = value
        mapdata_list.append({"name":key, "value":value})

    # 结果封装
    result = {}
    show_news_date_list = sorted(show_news_date_list, key=lambda x: x['time'], reverse=True) # 将新闻按照时间降序排序
    result["news_views_data"] = show_news_date_list # 返回左上角和右上角的新闻数据
    result["news_views_time_data"] = show_news_date_list # 返回根据时间排序的新闻
    result["news_views_crisis_data"] = show_news_crisis_list # 返回根据风险度排序的新闻
    result['map_data'] = {  # 地图数据
        "max": max_views,
        "min": 0,
        "data": mapdata_list
    }
    result['hot_data'] = {  # 下左数据
        'data': [[date_list[i], hot_num[i]] for i in range(len(date_list))]
    }
    result['sentiment_data'] = {    #下中数据
        'sentiment_date': date_list,
        'sentiment_pos': sentiment_pos,
        'sentiment_neg': sentiment_neg
    }

    # 右下角气泡图数据封装
    legend_data = []
    series_data = []
    for key, value in crisis_data.items():
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

    # print(str(midend-start))
    # print(str(end-start))
    # return JsonResponse({"foo":"title"})

    if cathe_flag:
        # 将查询结果进行缓存
        pkwf = open(cache_file_name,"wb") 
        pickle.dump(result, pkwf) 
    return JsonResponse(result)

# 综合选题页面查询函数
@csrf_exempt    #关闭csrf保护功能
def search_xuanti(request):

    # 前端查询参数处理
    # all_theme = False
    # all_content = True
    all_time = True
    all_keywords = True
    default_info = False

    # 主题处理
    theme = request.GET['theme']   # 主题参数
    # theme = '南海'   # 主题参数
    
    # 如果参数列表(dict类型)中没有language字段, 则返回默认值
    language = request.GET.get('language', '中文') # 语言参数

    '''
    try:
        language = request.GET['language'] # 语言参数
        print("lack of language para")
    except:
        language = '中文'
    '''

    # 如果没有
    if language == "":
        language = '中文'

    # language = "韩文"
    language_dict = { # 数据库字段写的时候脑抽了....
        "英文": "英语",
        "日文": "日语",
        "韩文": "韩语"
    }

    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d') 

    # 关键词处理
    words = request.GET['kws'].strip()
    # words = []
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False
    
    # 刚刚进入子页面, 未选择时间时的参数状态
    if start_time == end_time:
        if language == "中文" and all_keywords: # 如果时间相同,关键词为空且语言为中文, 则为默认值, 从缓存中获取要展示的信息
            default_info = True
        else:
            start_time = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d')
            end_time = datetime.datetime.strptime('2020-10-01', '%Y-%m-%d')
        
    pageno = int(request.GET['pageno']) # 当前页面编号
    pagesize = int(request.GET['size']) # 页面数据个数


    
    # 从主页面初次点进二级页面后的默认数据
    if default_info:
        # 根据theme检查缓存
        search_key = theme + "_mainpage"
        cache_file_dir = os.path.join(BASE_DIR, "WuhanBackend/cache/")
        cache_file_name = os.path.join(BASE_DIR, "WuhanBackend/cache/" + search_key + ".pkl")
        
        newsid_list = []
        # 从主页面数据缓存中获取主页面的展示数据, 然后记录其新闻id, 从数据库中查询全部信息
        if not os.path.exists(cache_file_name): # 如果缓存文件不存在
            news_views_list = main_news_show(theme)
            for news in news_views_list:
                newsid_list.append(news['newsid'])
        else:
            pkl_rf = open(cache_file_name,'rb')
            main_result = pickle.load(pkl_rf)
            for news in main_result['news_views_data']:
                newsid_list.append(news['newsid'])
        # print(len(newsid_list))
        q = Q(newsid__in=newsid_list) # 根据id列表筛选数据
        news_queryset = Newsinfo.objects.filter(q).order_by('-time')

    # 二级页面的数据查询处理
    else:
        if language != "中文":
            q = Q()
            q = q & Q(theme_label=theme) & Q(language=language_dict[language])
            
            if all_keywords is False: # 具有关键词限制
                tmp_q = Q()
                for word in words_list:
                    # tmp_q = tmp_q | Q(title__contains=word) # 关键词之间是'或'的关系, 使用该模式的话会由于前面的Q()而使其查询结果为全集
                    tmp_q = tmp_q & Q(title__contains=word) # 关键词之间是'与'的关系
                q = q & tmp_q
            news_queryset = Othernewsinfo.objects.filter(q).order_by('-time')
        else:
            # 组合参数查询, 利用Q的多条件查询
            q = Q()
            q = q & Q(theme_label=theme)
            q = q & Q(time__range=(start_time, end_time))
            
            if all_keywords is False: # 具有关键词限制
                tmp_q = Q()
                for word in words_list:
                    # tmp_q = tmp_q | Q(title__contains=word) # 关键词之间是'或'的关系, 使用该模式的话会由于前面的Q()而使其查询结果为全集
                    tmp_q = tmp_q & Q(title__contains=word) # 关键词之间是'与'的关系
                q = q & tmp_q

            # 查询语句
            news_queryset = Newsinfo.objects.filter(q).order_by('-time')
    
    
    newsList = []
    
    # 根据title去重
    title_set = set() # 用于title去重
    
    for new in news_queryset:
        if new.title not in title_set:
            title_set.add(new.title)
            new.title = new.title.replace("原创",'').replace("转帖",'').replace("参考消息",'') # 过滤title信息
            new.reliability = int(new.reliability) # 将新闻的可靠性指数归为整数
            newsList.append(model_to_dict(new))
    
    totalElements = len(newsList)

    newsList = newsList[(pageno - 1) * pagesize: pageno * pagesize] # 根据前端分页进行切片处理


    # 数据返回封装
    result = {}

    result['newsList'] = newsList
    result['totalElements'] = totalElements

    return JsonResponse(result)

# 专家观点页面查询函数
def search_view(request):
    
    # 前端查询参数处理
    all_keywords = True
    default_info = False # 默认展示数据
    
    # 主题处理
    theme = request.GET['theme']   # 主题参数
    
    # 时间处理    
    start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')

    # 关键词处理
    words = request.GET['kws'].strip()
    if len(words) > 0:
        words_list = re.split(' |,|，|;|：', words)
        all_keywords = False  
    
    # 刚进入观点页面的展示情况
    if start_time == end_time:
        if all_keywords: # 时间相同、关键词为空, 则为默认值
            default_info = True
        else:   # 如果关键词不为空, 则设置默认时间
            start_time = datetime.datetime.strptime('2020-01-01', '%Y-%m-%d')
            end_time = datetime.datetime.strptime('2020-10-01', '%Y-%m-%d')

    pageno = int(request.GET['pageno']) # 当前页面编号
    pagesize = int(request.GET['size']) # 页面数据个数
    

    
    # 观点页面的查询逻辑
    if default_info:
        # 根据theme检查缓存
        search_key = theme + "_mainpage"
        cache_file_dir = os.path.join(BASE_DIR, "WuhanBackend/cache/")
        cache_file_name = os.path.join(BASE_DIR, "WuhanBackend/cache/" + search_key + ".pkl")

        viewid_list = []
        # 从主页面数据缓存中获取主页面的展示数据, 然后记录所有的观点id, 从数据库中查询全部信息 
        if not os.path.exists(cache_file_name): # 如果缓存文件不存在
            # 从主页面数据缓存中获取主页面的展示数据, 然后记录所有的观点id, 从数据库中查询全部信息
            news_views_list = main_news_show(theme) 
            for news in news_views_list:
                for v in news['views']:
                    viewid_list.append(v['viewid'])
        else:
            pkl_rf = open(cache_file_name,'rb')
            main_result = pickle.load(pkl_rf)
            for news in main_result['news_views_data']:
                for v in news['views']:
                    viewid_list.append(v['viewid'])

        view_q = Q(viewid__in=viewid_list) # 根据id列表筛选数据    
    else:
        view_q = Q(newsid__theme_label=theme) # 跨表查询符合条件的view, 正向关联
        view_q = view_q & Q(time__range=(start_time, end_time))
        if all_keywords is False: # 具有关键词限制
            per_q = Q()
            for word in words_list:
                per_q = per_q | Q(personname__contains=word)
            
            content_q = Q()
            for word in words_list:
                # content_q = content_q | Q(viewpoint__contains=word) # 关键词之间是'或'的关系
                content_q = content_q & Q(viewpoint__contains=word) # 关键词之间是'与'的关系
            view_q = view_q & (per_q | content_q)

    

    
    # 查询语句
    views_queryset = Viewsinfo.objects.filter(view_q).order_by('-time')
    # totalElements = len(views_queryset)
    # views_queryset = views_queryset[(pageno - 1) * pagesize: pageno * pagesize] # 根据前端分页进行切片处理


    # 数据返回封装
    result = {}
    view_list = []
    view_per_list = [] # 有专家人名的观点
    view_noper_list = [] # 没有专家人名的观点数据
    
    # result['viewsList'] = []
    view_set = set() # 观点数据去重处理
    for view in views_queryset:
        # 此时可以直接通过view.newsid来获取news的相关信息
        # if view.newsid.theme_label == theme:    # 两个条件的筛选并集
        # print(type(view.newsid))
        if view.viewpoint in view_set:
            continue
        view_tmp = model_to_dict(view)
        
        # 根据国家补全机构
        if view_tmp['orgname'] == '':
            view_tmp['orgname'] = view_tmp['country']
        
        view_tmp['time'] = view_tmp['time'].strftime('%Y-%m-%d') 
        view_tmp['newsinfo'] = {
            'title': view.newsid.title,
            'time': view.newsid.time.strftime('%Y-%m-%d'),
            'content': view.newsid.content,
            'theme': view.newsid.theme_label,
            'source': view.newsid.customer
        }
        # print(view_tmp)
        # view_list.append(view_tmp)
        if view_tmp['personname'] == '':
            view_noper_list.append(view_tmp)    
        else:
            view_per_list.append(view_tmp)

        view_set.add(view.viewpoint)

    view_list = view_per_list + view_noper_list
    totalElements = len(view_list)
    result['viewsList'] = view_list[(pageno - 1) * pagesize: pageno * pagesize]
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
    cathe_flag = True # 不使用cache, 如果事件分析页面算法进行更改则之前的cache全部都需要作废
        
    # 主题处理
    theme = request.GET['theme']   # 主题参数

    # 时间处理    
    # start_time = datetime.datetime.strptime(request.GET['date_from'], '%Y-%m-%d')
    end_time = datetime.datetime.strptime(request.GET['date_to'], '%Y-%m-%d')
    # 获取30天内的数据进行分析
    delta_time = datetime.timedelta(days=30)  
    start_time = end_time - delta_time
    
    '''
    if start_time != end_time:
        # print("start_time != end_time")
        all_time = False # 如果两者时间不同, 则有时间限制
    else: # 两者时间相同, 给出默认时间
        start_time = datetime.datetime.strptime('2020-09-01', '%Y-%m-%d')
        end_time = datetime.datetime.strptime('2020-10-01', '%Y-%m-%d')
    '''

    # 根据theme与start_time, end_time检查缓存
    search_key = theme + "_" + start_time.strftime("%Y%m%d") + "_" + end_time.strftime("%Y%m%d")
    cache_file_dir = os.path.join(BASE_DIR, "WuhanBackend/cache/")
    cache_file_name = os.path.join(BASE_DIR, "WuhanBackend/cache/" + search_key + ".pkl")
    # cache_file_name = "WuhanBackend/cache/" + search_key + ".pkl"
    if not os.path.exists(cache_file_dir):   # 文件夹不存在则创建文件夹
        os.mkdir(cache_file_dir)
    if cathe_flag and os.path.exists(cache_file_name): # 缓存已经存在
        pkl_rf = open(cache_file_name,'rb')
        result = pickle.load(pkl_rf)
        return JsonResponse(result)


    # 组合参数查询, 利用Q的多条件查询
    q = Q()
    q = q & Q(theme_label=theme)
    q = q & Q(time__range=(start_time, end_time))

    # 查询语句
    news_queryset = Newsinfo.objects.filter(q).order_by('-time')
    # print(news_queryset.count())

    # 遍历新闻数据, 获取相关信息
    newsid_set = set()
    time_news_dict = {}
    nextevent_dict = {} # 事件预测字典处理 {event: weight}
    nextevent_news = {} # 事件预测触发新闻title {event: newslist}
    nextevent_views = {} # 事件预测的支撑观点(从支撑新闻中选取) {event: newsid_list}

    nextevent_news_pro = {}
    nextevent_views_pro = {}

    nextevent_graph_data = {} # 根据支撑素材构造的图谱数据
    per_set = set() # 用于节点去重
    org_set = set()
    media_set = set()
    tri_set = set()
    
    title_set = set() # 根据title进行去重
    # 根据查询日期按天递增构建初始化字典
    nowtime = start_time
    delta_time = datetime.timedelta(days=1) # 用于时间轴的不连续问题 
    while nowtime <= end_time:
        time_news_dict[nowtime.strftime('%Y-%m-%d')] = []
        nowtime += delta_time
    for n in news_queryset:
        # print(type(news.viewsinfo_set))
        n_title = n.title.replace("原创",'').replace("转帖",'').replace("参考消息",'')
        # 根据新闻title进行去重
        if n_title in title_set:
            continue
        newsid_set.add(n.newsid)
        time_str = n.time.strftime('%Y-%m-%d')
        if time_str in time_news_dict:
            time_news_dict[time_str].append(n)
        else:
            print("search_eventa time_news_dict error: time_str not in start_time-end_time")
        
        # 事件预测数据处理
        event_list = n.nextevent.split(',') # 根据','分割多个候选事件
        for e in event_list:
            e_str, weight = e.split(':')
            if e_str in nextevent_dict:
                if e_str != '无风险事件':
                    nextevent_dict[e_str] += int(weight)
                    nextevent_news[e_str].append(n_title + " " + time_str + " " + n.customer)
                    nextevent_views[e_str].append(n.newsid)
                    
                    # 增加支撑新闻信息
                    tmp = {}
                    tmp['id'] = n.newsid
                    tmp['title'] = n_title
                    tmp['content'] = n.content
                    tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
                    tmp['source'] = n.customer
                    tmp['crisis'] = n.crisis
                    # 增加NEW、MEDIA类型的节点
                    nextevent_graph_data[e_str]['nodelist'].append(
                        {
                            "ID": n.newsid,
                            "name": n_title + " " + n.time.strftime('%Y-%m-%d %H:%M:%S'),
                            "type": "NEW",
                            "weight": 1
                        }
                    )
                    if n.customer not in media_set:
                        nextevent_graph_data[e_str]['nodelist'].append(
                            {
                                "ID": n.customer,
                                "name": n.customer,
                                "type": "MEDIA",
                                "weight": 1
                            }
                        )
                        media_set.add(n.customer)
                    nextevent_graph_data[e_str]['linklist'].append(
                        {
                            "SourceID": n.newsid,
                            "TargetID": n.customer,
                            "weight": 1
                        }
                    )
                    # 处理新闻title, 根据新闻危机词高亮新闻title, 在原字符串增加html高亮标签
                    wjword_set = set()
                    wjword_set.add("侦察")
                    wjword_set.add("两岸")
                    wjword_set.add("民进党")
                    wjword_set.add("国民党")
                    wjword_set.add("统一")
                    wjword_set.add("胜选")
                    wjword_set.add("选情")
                    wjword_set.add("民心")
                    wjword_set.add("民主")
                    wjword_set.add("独立")
                    wjword_set.add("导弹")
                    wjword_set.add("动武")
                    if n.crisis > 0:
                        for wjwords in n.wjwords.split(" "):
                            trigger = wjwords.split(":")[0]
                            # 增加 NEW 与 Tri 之间的关系
                            if trigger not in tri_set:
                                nextevent_graph_data[e_str]['nodelist'].append(
                                    {
                                        "ID": trigger,
                                        "name": trigger,
                                        "type": "TRIGGER",
                                        "weight": 1
                                    }
                                )
                                tri_set.add(trigger)
                            nextevent_graph_data[e_str]['linklist'].append(
                                {
                                    "SourceID": n.newsid,
                                    "TargetID": trigger,
                                    "weight": 1
                                }
                            )
                            for w in wjwords.split(":")[0].split("-"):
                                if len(w) > 0: wjword_set.add(w)
                    
                    for w in wjword_set:
                        html_str = '<span style="color: red;">' + w + '</span>'
                        tmp['title'] = tmp['title'].replace(w, html_str)

                    nextevent_news_pro[e_str].append(tmp)
                    
                else:
                    nextevent_dict[e_str] += int(weight)
            else:
                if e_str != '无风险事件':
                    nextevent_dict[e_str] = int(weight)
                    nextevent_news[e_str] = [n_title + " " + time_str + " " + n.customer]
                    nextevent_views[e_str] = [n.newsid]
                    nextevent_graph_data[e_str]['nodelist'] = []
                    nextevent_graph_data[e_str]['linklist'] = []

                    # 增加支撑新闻信息
                    tmp = {}
                    tmp['id'] = n.newsid
                    tmp['title'] = n_title
                    tmp['content'] = n.content
                    tmp['time'] = n.time.strftime('%Y-%m-%d %H:%M:%S')
                    tmp['source'] = n.customer
                    tmp['crisis'] = n.crisis

                    # 增加NEW、MEDIA类型的节点
                    nextevent_graph_data[e_str]['nodelist'].append(
                        {
                            "ID": n.newsid,
                            "name": n_title + " " + n.time.strftime('%Y-%m-%d %H:%M:%S'),
                            "type": "NEW",
                            "weight": 1
                        }
                    )
                    if n.customer not in media_set:
                        nextevent_graph_data[e_str]['nodelist'].append(
                            {
                                "ID": n.customer,
                                "name": n.customer,
                                "type": "MEDIA",
                                "weight": 1
                            }
                        )
                        media_set.add(n.customer)
                    nextevent_graph_data[e_str]['linklist'].append(
                        {
                            "SourceID": n.newsid,
                            "TargetID": n.customer,
                            "weight": 1
                        }
                    )

                    # 处理新闻title, 根据新闻危机词高亮新闻title, 在原字符串增加html高亮标签
                    wjword_set = set()
                    wjword_set.add("侦察")
                    wjword_set.add("两岸")
                    wjword_set.add("民进党")
                    wjword_set.add("国民党")
                    wjword_set.add("统一")
                    wjword_set.add("胜选")
                    wjword_set.add("选情")
                    wjword_set.add("民心")
                    wjword_set.add("民主")
                    wjword_set.add("独立")
                    wjword_set.add("导弹")
                    wjword_set.add("动武")
                    if n.crisis > 0:
                        for wjwords in n.wjwords.split(" "):
                            trigger = wjwords.split(":")[0]
                            # 增加 NEW 与 Tri 之间的关系
                            if trigger not in tri_set: # 如果未出现过改节点则新加
                                nextevent_graph_data[e_str]['nodelist'].append(
                                    {
                                        "ID": trigger,
                                        "name": trigger,
                                        "type": "TRIGGER",
                                        "weight": 1
                                    }
                                )
                                tri_set.add(trigger)
                            nextevent_graph_data[e_str]['linklist'].append(
                                {
                                    "SourceID": n.newsid,
                                    "TargetID": trigger,
                                    "weight": 1
                                }
                            )
                            for w in wjwords.split(":")[0].split("-"):
                                wjword_set.add(w)
                    
                    for w in wjword_set:
                        html_str = '<span style="color: red;">' + w + '</span>'
                        tmp['title'] = tmp['title'].replace(w, html_str)

                    nextevent_news_pro[e_str] = [tmp]


                else:
                    nextevent_dict[e_str] = int(weight)
                    nextevent_news[e_str] = []
        
        title_set.add(n_title)
    # print(time_news_dict)

    # 依据事件预测新闻材料的观点展示
    nextevent_views_data = []
    view_set = set()
    views_show_num = 15
    total_weight = 0 # 事件预测总权重
    for e, w in nextevent_dict.items():
        total_weight += w   # 计算总权重
    
    # 加载关键专家字典
    with codecs.open(os.path.join(BASE_DIR,"WuhanBackend/dict/theme_person.json"),'r','utf-8') as rf:
        theme_person_dict = json.load(rf)

    for e_str, newsid_list in nextevent_views.items():
        view_query_tmp = Viewsinfo.objects.filter(newsid__in=newsid_list)
        views_list = []
        view_set = set()
        for v in view_query_tmp:
            sim_flag = False
            if v.viewpoint in view_set: continue    # 观点去重
            if len(v.viewpoint) < 10: continue 
            if len(v.orgname + v.pos + v.personname) < 2: continue
            for old_v in view_set:
                if fuzz.partial_ratio(v.viewpoint, old_v) > 70:
                    sim_flag = True
                    break
            if sim_flag: continue
            if v.personname in theme_person_dict: # 从特定的专家字典中展现观点数据
                views_list.append(
                    {
                        "org": theme_person_dict[v.personname]['org'] + v.personname,
                        "viewpoint": v.verb + v.viewpoint,
                        "eventname": e_str,
                        "time": v.time.strftime('%Y-%m-%d %H:%M:%S'),
                        "weight": theme_person_dict[v.personname]['weight'],
                        "recommend": 1,
                    }
                )
                # 增加观点节点
                nextevent_graph_data[e_str]['nodelist'].append(
                    {
                        "ID": v.viewid,
                        "name": v.verb + v.viewpoint + " " + v.time.strftime('%Y-%m-%d %H:%M:%S'),
                        "type": "VIEW",
                        "weight": 1
                    }
                )
                # 增加新闻与人名之间的关系
                nextevent_graph_data[e_str]['linklist'].append(
                    {
                        "SourceID": v.newsid,
                        "TargetID": v.personname,
                        "weight": 1
                    }
                )
                # 增加人名节点
                if v.personname not in per_set:
                    nextevent_graph_data[e_str]['nodelist'].append(
                        {
                            "ID": v.personname,
                            "name": v.personname,
                            "type": "PERSON",
                            "weight": 1
                        }
                    )
                    per_set.add(v.personname)
                # 增加人名与观点间的关系
                nextevent_graph_data[e_str]['linklist'].append(
                    {
                        "SourceID": v.viewid,
                        "TargetID": v.personname,
                        "weight": 1
                      }
                )
                # 增加职位节点
                if v.orgname + v.pos not in org_set:
                    nextevent_graph_data[e_str]['nodelist'].append(
                        {
                            "ID": v.orgname + v.pos,
                            "name": v.orgname + v.pos,
                            "type": "ORG",
                            "weight": 1
                        }
                    )
                    org_set.add(v.orgname + v.pos)
                # 增加人名与职位间的关系
                nextevent_graph_data[e_str]['linklist'].append(
                    {
                        "SourceID": v.personname,
                        "TargetID": v.orgname + v.pos,
                        "weight": 1
                    }
                )
            else:
                views_list.append(
                    {
                        "org": v.orgname + v.pos + v.personname,
                        "viewpoint": v.verb + v.viewpoint,
                        "eventname": e_str,
                        "time": v.time.strftime('%Y-%m-%d %H:%M:%S'),
                        "weight": 1,
                        "recommend": 0
                    }
                )
                if len(v.personname) > 1: # 人名字符串长度大于1才进行处理
                    # 增加观点节点
                    nextevent_graph_data[e_str]['nodelist'].append(
                        {
                            "ID": v.viewid,
                            "name": v.verb + v.viewpoint + " " + v.time.strftime('%Y-%m-%d %H:%M:%S'),
                            "type": "VIEW",
                            "weight": 1
                        }
                    )
                    # 增加新闻与人名之间的关系
                    nextevent_graph_data[e_str]['linklist'].append(
                        {
                            "SourceID": v.newsid,
                            "TargetID": v.personname,
                            "weight": 1
                        }
                    )
                    # 增加人名与观点间的关系
                    if v.personname not in per_set:
                        nextevent_graph_data[e_str]['nodelist'].append(
                            {
                                "ID": v.personname,
                                "name": v.personname,
                                "type": "PERSON",
                                "weight": 1
                            }
                        )
                        per_set.add(v.personname)
                    nextevent_graph_data[e_str]['linklist'].append(
                        {
                            "SourceID": v.viewid,
                            "TargetID": v.personname,
                            "weight": 1
                        }
                    )

                    if len(v.orgname + v.pos) > 2:
                        # 增加人名与职位间的关系
                        if v.orgname + v.pos not in org_set:
                            nextevent_graph_data[e_str]['nodelist'].append(
                                {
                                    "ID": v.orgname + v.pos,
                                    "name": v.orgname + v.pos,
                                    "type": "ORG",
                                    "weight": 1
                                }
                            )
                            org_set.add(v.orgname + v.pos)
                        nextevent_graph_data[e_str]['linklist'].append(
                            {
                                "SourceID": v.personname,
                                "TargetID": v.orgname + v.pos,
                                "weight": 1
                            }
                        )




            view_set.add(v.viewpoint)
        views_list = sorted(views_list, key=lambda x: x['weight'], reverse=True) # 根据观点时间降序排序
        nextevent_views_pro[e_str] = views_list

    # 事件分析左上角趋势处理
    tendency_time = [] # 用于事件分析页面的趋势数据
    tendency_news = []
    
    timeline_news = [] # 时间轴的新闻数据列表
    for time, newslist in time_news_dict.items():
        # 趋势图数据处理
        tendency_time.append(time)
        news_count = len(newslist) # 当天的新闻数量

        # 根据crisis字段对newslist进行排序
        newslist = sorted(newslist, key=lambda x: x.crisis, reverse=True) # 根据危机指数进行降序排序

        if news_count == 0:  # 当天没有检索到新闻的情况
            tendency_news.append({
                'name': 'None',
                'value': 0, # 实际曲线
                'predict_value': 10,
                'crisis_value': 0
            })
        else:
            title_tmp = newslist[0].title.replace("原创",'').replace("转帖",'').replace("参考消息",'') # 每天的高风险事件筛选
            # 计算风险度均值
            crisis_count = 0
            for n in newslist:
                crisis_count += n.crisis
            crisis_count = float("%.2f" % (float(crisis_count) / news_count))

            tendency_news.append({
                'name': title_tmp,
                'value': news_count, # 实际趋势曲线
                'predict_value': news_count + 10, # 预测曲线
                'crisis_value': crisis_count
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

    
    nextevent_content = {   # 20201011 提供的意见, 增加预测事件的解释, 二期时候可以做成json文件进行读取
        "无风险事件": "其它",
        "美国在南海挑起争端": "指美国采取南海“航行自由”行动、美国发表挑起南海争端的言论等挑衅事件",
        "中方采取反制措施": "指中方在南海进行军事演习、在南海岛礁部署新的军事力量、发布相关的外交声明等相关反制事件",
        "朝鲜采取军事行动等过激行为": "指朝试射/部署导弹、进行核试验、进行炮击等不利于半岛局势的事件",
        "西方国家针对朝鲜进行制裁": "指在韩的军事部署、对朝方的外交谴责、对朝方的经济封锁等制裁事件",
        "台湾政局核心人物鼓吹台独": "指台湾民间、政坛等组织团体掀起台独浪潮等不利于两岸统一的事件",
        "台湾政局发生大规模人事变化": "指台湾各级政府因选举等行为而发生的较大人事调整事件"
    }
    del nextevent_dict['无风险事件'] # 从字典中剔除"无风险事件"
    eventpre_data = {
        'legend_data': list(nextevent_dict.keys()),
        'data': [{'name': x, 'value': y, 'news': nextevent_news[x], 'name_content': nextevent_content[x]} for x, y in nextevent_dict.items()],
        'data_pro': [{'name': x, 'value': float(y)/total_weight, 'name_content': nextevent_content[x]} for x, y in nextevent_dict.items()]
    }
    
    # print(eventpre_data)

    # 数据返回封装
    result = {}
    result['tendency_data'] = tendency_data # 用于时间-趋势图
    result['eventpre_data'] = eventpre_data # 用于事件预测模块
    result['timeline_data'] = timeline_data # 用于时间轴数据处理
    result['nextevent_news_pro'] = nextevent_news_pro # 用于事件预测的支撑材料
    result['nextevent_views_pro'] = nextevent_views_pro # 用于事件预测的支撑观点
    
    if cathe_flag:
        # 将查询结果进行缓存
        pkwf = open(cache_file_name,"wb") 
        pickle.dump(result, pkwf) 

    # return JsonResponse({"foo":"title"})
    return JsonResponse(result)



   