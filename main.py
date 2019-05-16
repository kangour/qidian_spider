import os
import time
import requests
import collections
from bs4 import BeautifulSoup
from multiprocessing import Pool
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


'''
爬取：起点小说，采集限时免费小说，下载保存慢慢看

作者：不才
邮箱：laobingm@qq.com
结构：Base 请求基类，Soup 数据爬取，Parser 通用元素解析，Pager 页面数据解析，Operater 操作部分，Store 文件存储
待做：多线程同步爬取和下载，Session 缓存，Except 异常处理
日期：2019年5月15日
更新：2019年5月21日
协作：

'''

class Base():
    def __init__(self):
        self._http = requests.Session()

    def handle_result(self, res):
        return res

    def request(self, method, url, **kwargs):
        res = self._http.request(
            method=method,
            url=url,
            **kwargs
        )
        return self.handle_result(res)

    def get(self, url, **kwargs):
        return self.request(
            method='get',
            url=url,
            **kwargs
        )

    def post(self, url, **kwargs):
        return self.request(
            method='post',
            url_or_endpoint=url,
            **kwargs
        )


class Soup(Base):
    def __init__(self, target):
        super().__init__()
        self.soup = self.get_soup(target)

    def get_html(self, target):
        res = self.get(url=target)
        return res.text

    def get_soup(self, target):
        html = self.get_html(target)
        soup = BeautifulSoup(html, 'lxml')
        return soup


class Parser():
    def __init__(self, target):
        self.soup = Soup(target).soup

    def get_element(self, tag, attrs={}, find_all=False):
        if find_all is False:
            return self.soup.find(name=tag, attrs=attrs)
        else:
            return self.soup.find_all(name=tag, attrs=attrs)

    @staticmethod
    def get_element_by_subsoup(soup, tag, attrs={}, find_all=False):
        if find_all is False:
            return soup.find(name=tag, attrs=attrs)
        else:
            return soup.find_all(name=tag, attrs=attrs)

    @staticmethod
    def format_url(target):
        if target.startswith('//'):
            target = 'https:' + target
        return target


class Pager(Parser):
    def __init__(self, target):
        target = self.format_url(target)
        super().__init__(target)

    def free(self):
        element = self.get_element('a', {'data-eid': 'qd_A18'})
        logger.info(element['href'])
        return element['href']

    def storys(self):
        element = self.get_element('div', {'class': 'book-img-text'})
        element = self.get_element_by_subsoup(element, 'li', find_all=True)
        dic = collections.OrderedDict()
        for i in element:
            i = self.get_element_by_subsoup(i, 'a', {'data-eid': 'qd_E05'})
            dic[i.text] = i['href']
        logger.info(dic)
        return dic

    def describe(self):
        res = ''
        element = self.get_element('a', {'class': 'writer', 'data-eid': 'qd_G08'})
        logger.info(element.text)
        res += '作者：' + element.text + '\n'
        element = self.get_element('p', {'class': 'intro'})
        logger.info(element.text)
        res += '介绍：' + element.text + '\n'
        return res

    def chapters(self):
        element = self.get_element('a', {'data-eid': 'qd_G55'}, find_all=True)
        dic = collections.OrderedDict()
        for i in element:
            logger.info('%s %s' % (i.text, i['href']))
            dic[i.text] = i['href']
        return dic

    def content(self):
        element = self.get_element('div', {'class': 'read-content j_readContent'})
        text = element.text
        logger.info(text)
        return text


class Store():
    def __init__(self, filename='result', suffix='.txt', path='./'):
        self.filename = filename
        self.suffix = suffix
        self.path = path
        self.check_filename()

    def check_filename(self):
        '''
        清理同名文件
        '''
        for f in os.listdir(self.path):
            if os.path.isfile(filename) and f == self.filename + self.suffix:
                os.remove(os.path.join(self.path, f))

    def writer(self, *content):
        with open(self.path + self.filename + self.suffix, 'a') as f:
            for i in content:
                f.write(i)
                f.write('\n\n')


class Operater():
    def __init__(self, target):
        self.page = Pager(target)

    def get_storys(self):
        target = self.page.free()
        page = Pager(target)
        storys = page.storys()
        return storys

    def get_chapters(self):
        chapters = self.page.chapters()
        return chapters

    def get_describe(self):
        describe = self.page.describe()
        return describe

    def get_content(self):
        content = self.page.content()
        return content


def spider(story):
    story_name = story[0]
    story_url = story[1]
    store = Store(story_name)
    logger.info('%s %s' % (story_name, story_url))

    operater = Operater(story_url)
    chapters = operater.get_chapters()
    describe = operater.get_describe()
    store.writer(story_name, describe)
    logger.info('%s 共 %s 个章节' % (story_name, len(chapters)))
    n = 1
    for chapter in chapters:

        operater = Operater(chapters[chapter])
        content = operater.get_content()
        store.writer(content)
        logger.info('%s 获取完成！' % chapter)
        logger.info("%s 已完成:%.2f%%" % (story_name, float(n / len(chapters))))
        n += 1
        time.sleep(1)


if __name__ == '__main__':
    homepage = 'https://www.qidian.com/'

    operater = Operater(homepage)
    storys = operater.get_storys()
    logger.info('书本获取完成！')
    print('\n\n\n')
    # 多进程，每个进程对应一本书
    p = Pool(10)
    while(True):
        for i in range(10):
            if len(storys) == 0:
                break
            p.apply_async(spider, args=(storys.popitem(),))
        p.close()
        p.join()

