# -*- coding: UTF-8 -*-

#                        .::::.
#                      .::::::::.
#                     :::::::::::
#                  ..:::::::::::'
#               '::::::::::::'
#                 .::::::::::
#            '::::::::::::::..
#                 ..:::::::::::::.
#               ``:::::::::::::::::
#                ::::``::::::::::'       .:::.
#               ::::'   ':::::'       .::::::::.
#             .::::'      ::::     .:::::::'::::.
#            .:::'       :::::  .:::::::::' ':::::.
#           .::'        :::::.:::::::::'      ':::::.
#          .::'         ::::::::::::::'         ``::::.
#      ...:::           ::::::::::::'              ``::.
#     ```` ':.          ':::::::::'                  ::::..
#                        '.:::::'                    ':'````..
#                     Beauty bless never bug

import re
from fuzzywuzzy import fuzz
import codecs

# 依据新闻的评论计算新闻的影响力指数
# news_df 为pandas中df类型数据
# 返回值result为字典类型数据
def news_comment_deal(news_df):
    comment_news = news_df.dropna(subset=["content", "title", "comments"]) # 删除content, title, comments中值为Nan的行
    result = {}
    influence_list = []
    for index, row in comment_news.iterrows():
        news_id = row['news_id']
        influence_rate = 0
        comment_list = []
        # 依据每条评论的agreeCount与against 计算新闻的影响力  
        for comment in eval(row['comments']):  # 利用eval函数将字符串转换成list形式
            # comment = json.loads(comment)
            total_count = comment['against'] + comment['agreeCount']
            influence_rate += total_count + 10 # 评论支持数 + 评论反对数 + 10(评论权重)
            influence_list.append(influence_rate) # 用于后续对影响力参数进行调整
            comment['totalCount'] = total_count
            comment_list.append(comment)
            
                
        comment_list = sorted(comment_list,key = lambda e:e.__getitem__('totalCount'), reverse=True) # 依据totalCount对评论进行从大到小排序
        
        result[news_id] = {
            'influence_rate': influence_rate,
            'comment_list': comment_list
        }
    # 更新result中的影响力指数数据, 将数值映射到0-100
    max_influence = max(influence_list)

    for key in result.keys():
        result[key]['influence_rate'] = result[key]['influence_rate'] / max_influence * 100

    return result


# 计算文本相似度(基于编辑距离)
def text_sim(s1, s2):
    return fuzz.ratio(s1, s2)

# 文本清洗
def clean_zh_text(text, cleantype=1):
    result = text
    if cleantype == 1:
        result = ''.join(text.split()) #split方法中不带参数时，表示分割所有换行符、制表符、空格
        # content = content.replace(u'\u3000', u'').replace('\n','').replace(' ','').replace('\r','')
    elif cleantype == 2:
        
        # keep English, digital and Chinese
        text = text.replace('，',',').replace('。','.').replace('？','?').replace('！','!').replace('：',':') # 将英文标点转换为中文标点
        comp = re.compile('[^A-Z^.^,^!^?^:^a-z^0-9^\u4e00-\u9fa5]')
        result = comp.sub('', text)
    else:
        print("type error in utils.clean_zh_text")
    return result

