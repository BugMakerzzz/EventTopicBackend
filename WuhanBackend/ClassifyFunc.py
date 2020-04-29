import codecs
from typing import Iterator, List, Dict

class ClassifyFunc:
    def __init__(self):
        self.word_country_dict = self._load_dict("dict/国家分类.txt", dict_type=1)    # 国家关键词字典
        self.word_content_dict = self._load_dict("dict/内容分类.txt", dict_type=2)    # 内容关键词字典

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ClassifyFunc, cls).__new__(cls)
        return cls.instance

    # 加载字典, dict_type=1为国家字典, dict_type=2为内容字典, 默认为国家字典
    # 返回值为dict类型
    def _load_dict(self, path:str, dict_type: int = 1) -> Dict:
        result_dict = {}
        word_country_dict = {}
        with codecs.open(path,"r","UTF-8") as rf:
            for line in rf.readlines():
                category, keywords = line.strip().split(":") # 类别: 关键词1, 关键词2, ....
                keywords = set(keywords.split(","))
                result_dict[category] = keywords
        return result_dict



    # 根据新闻标题进行分类, dict_type=1为国家标签的分类, dict_type=2为事件标签的分类
    # 返回值为标签类型
    def classify_title(self, title_words: List[str], dict_type:int = 1) -> str:
        # 首先加载关键词字典
        category_dict = self.word_country_dict if dict_type==1 else self.word_content_dict    # 加载关键词字典
        
        result_set = set()

        word_category_dict = {} # {word:category}, 此时一个单词对应一个事件类别, 未考虑多个一个单词对应多个事件类别的情况
        for category, keywords in category_dict.items():
            for w in keywords:
                word_category_dict[w] = category

        for w in title_words:
            if w in word_category_dict:
                result_set.add(word_category_dict[w])

        if len(result_set) == 0:
            result_set.add('其它')
        
        return ' '.join(result_set)

if __name__ == '__main__':
    
    classify_func = ClassifyFunc()
    title_words = ['菲', '总统', '杜特', '尔特', '警告', '美国', '：', '别', '在', '南', '海军', '演', '挑衅', '中国']
    print(classify_func.classify_title(title_words, 2))

