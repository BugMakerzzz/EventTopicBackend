# 负责处理前端的查询功能, 经由views调用发送到前端

from WuhanBackend.models import Newsinfo, Viewsinfo


# 根据时间范围筛选数据, 输入参数为datetime类型, 输出为Django的QuerySet类型
def get_news_by_time(start_time, end_time):
    news_queryset = Newsinfo.objects.filter(time__range=(start_time, end_time))
    # print(news_queryset)
    # print(type(news_queryset))
    return news_queryset

# 根据主题筛选数据, 输入参数为list<str>类型, 输出为Django的QuerySet类型
def get_news_by_theme(theme_list):
    news_queryset = Newsinfo.objects.filter(theme_label__in=theme_list)
    return news_queryset

# 多条件筛选数据, 输入为Django的q语句, 输出为Django的QuerySet类型
def get_news(q):
    news_queryset = Newsinfo.objects.filter(q)
    return news_queryset



