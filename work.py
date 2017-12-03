# coding=utf-8
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zhihu import Question

import os
import re
import requests
import html2text
import shutil
import subprocess
import smtplib
import redis


class ZhihuToMobi(object):
    def __init__(self, question_id):
        self.question_id = question_id
        self.question_path = None
        self.mobi_path = None

    def question(self, url):
        question = Question(url)

        title = question.get_title()  # 标题
        detail = question.get_detail()  # 描述
        answers_num = question.get_answers_num()  # 回答个数
        followers_num = question.get_followers_num()  # 关注人数
        topics = question.get_topics()  # 所属话题
        top_answers = question.get_top_i_answers(10)  # 前十回答

        return title, detail, answers_num, followers_num, topics, top_answers

    def answer_to_md(self, answer):
        content = answer.get_content()
        text = html2text.html2text(content.decode('utf-8')).encode("utf-8")
        r = re.findall(r'\*\*(.*?)\*\*', text)
        for i in r:
            if i != " ":
                text = text.replace(i, i.strip())

        r = re.findall(r'_(.*)_', text)
        for i in r:
            if i != " ":
                text = text.replace(i, i.strip())

        r = re.findall(r'!\[\]\((?:.*?)\)', text)
        for i in r:
            text = text.replace(i, i + "\n\n")

        p = re.compile(r'(http:\/\/.*\.zhimg\.com)/(.*)\)')
        r = p.findall(text)

        def func(m):
            url = m.group(1) + "/" + m.group(2)
            r = requests.get(url, stream=True)

            path = os.path.join(os.getcwd(), "images") + "/" + m.group(2)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
            return os.path.join(os.getcwd(), "images") + "/" + m.group(2) + ")"

        text = p.sub(func, text)
        return text

    def question_to_md(self, url):
        self.title, detail, answers_num, followers_num, topics, top_answers = self.question(url)
        self.question_path = os.path.join(os.path.join(os.getcwd(), "questions"), self.question_id + ".md")
        self.mobi_path = os.path.join(os.path.join(os.getcwd(), "mobis"), self.question_id + ".mobi")
        f = open(self.question_path, "a")
        f.write("\n")
        f.write("# " + self.title + "\n")
        f.write("## " + detail + "\n")
        f.write("### 回答数: " + str(answers_num) + " 关注数: " + str(followers_num) + "\n")
        f.write("——————————————————————————————————————————\n")
        for answer in top_answers:
            f.write("## 作者: " + answer.get_author().get_user_id() + "  赞同: " + str(answer.get_upvote()) + "\n")
            text = self.answer_to_md(answer)
            print text
            f.write(text)
            f.write("#### 原链接: " + answer.answer_url + "\n")
        f.close()

    def md_to_mobi(self):
        question_path = self.question_path
        mobi_path = self.mobi_path
        command1 = "ebook-convert %s %s  --markdown-extensions  --output-profile=kindle_pw --mobi-file-type=old \
            --mobi-ignore-margins --mobi-keep-original-images --no-inline-toc --remove-paragraph-spacing" % (
            question_path, mobi_path)
        ret1 = subprocess.call(command1, shell=True)
        title = self.title.replace(" ", "")
        command2 = "ebook-meta %s --authors zhihu --title %s " % (mobi_path, title)
        ret2 = subprocess.call(command2, shell=True)
        if ret1 != 0 and ret2 != 0:
            raise Exception("[%s] execute failed." % command1)
        else:
            return self.mobi_path


class MailToKindle(object):
    def __init__(self, mobi_path, email):
        self.mobi_path = mobi_path
        self.email = email

    def send_mail(self):
        msg = MIMEMultipart()

        # 附件
        att = MIMEText(open(self.mobi_path, 'rb').read(), 'base64', 'utf-8')
        att["Content-Type"] = 'application/octet-stream'
        att["Content-Disposition"] = 'attachment; filename="%s"' % self.mobi_path.split("/")[
            -1]

        # 邮件
        msg.attach(att)
        msg['to'] = self.email
        msg['from'] = '892917947@qq.com'
        msg['subject'] = 'kindle'

        # 发送
        try:
            # server = smtplib.SMTP()
            # server.connect('smtp.qq.com')
            server = smtplib.SMTP_SSL("smtp.qq.com", 465)
            server.login('892917947@qq.com', 'xxxxx')
            server.sendmail(msg['from'], msg['to'], msg.as_string())
            print '发送成功'
        except Exception, e:
            print "发送失败"
            print str(e)
        finally:
            server.quit()


def generate(url=None, email=None):
    if not url:
        url = "http://www.zhihu.com/question/22896560"
    if not email:
        email = "bo5509@kindle.cn"
    question_id = url.split("/")[-1]

    # 生成文本
    zm = ZhihuToMobi(question_id)
    zm.question_to_md(url)
    mobi_path = zm.md_to_mobi()

    # 文本发送到kindle
    mk = MailToKindle(mobi_path, email)
    mk.send_mail()


def get_redis():
    redis_conf = {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0
    }
    connection_pool = redis.ConnectionPool(host=redis_conf['host'], port=redis_conf['port'], db=redis_conf['db'])
    return redis.StrictRedis(connection_pool=connection_pool)


if __name__ == '__main__':
    redis = get_redis()
    while True:
        data = redis.brpop("kindle")
        if data:
            address = data[1].split(";")[0]
            email = data[1].split(";")[1]
            print address
            print email
            generate(address, email)
