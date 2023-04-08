from flask import Flask, request, jsonify
import os
import re
from sudachipy import tokenizer, dictionary
import collections
import json

ALLOWED_EXTENSION = 'txt'

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

def word_ranking(file):
    # トーク履歴の読み込み
    with open(file.filename) as f:
        talk = f.read()

    talk_list = talk.split()

    # トーク履歴から会話内容を抽出
    talk_put_together = ''
    time_pattern = re.compile(r"\d{1,2}:\d{2}")
    week_pattern = re.compile(r"(月|火|水|木|金|土|日)曜日")
    abbr_week_pattern = re.compile(r"\((月|火|水|木|金|土|日)\)")

    for i in range(1, len(talk_list)):
        time_match = re.search(time_pattern, talk_list[i])
        week_match = re.search(week_pattern, talk_list[i-1]) or re.search(abbr_week_pattern, talk_list[i-1])

        if time_match and not(week_match):
            talk_put_together += talk_list[i-1]

    # 会話内容から英数字と特殊記号を削除
    alphanumeric_pattern = re.compile('[a-zA-Z0-9]+')
    mark_pattern = re.compile('[!"#$%&\'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]')

    talk_put_together = alphanumeric_pattern.sub('', talk_put_together)
    cleaned_talk = mark_pattern.sub('', talk_put_together)

    # 一度にトークン化できるバイト数に制限があるため10,000字ごとに分割
    max_length = 10000
    split_cleaned_talk = [cleaned_talk[i:i+max_length] for i in range(0, len(cleaned_talk), max_length)]

    # 会話内容をトークン化
    token_object = []
    tokenizer_obj = dictionary.Dictionary().create()
    mode = tokenizer.Tokenizer.SplitMode.A

    for split in split_cleaned_talk:
        token_object += [m.surface() for m in tokenizer_obj.tokenize(split, mode)]

    # 名詞か形容詞に該当するトークンを抽出
    token_result = []

    for token in token_object:
        try:
            m = tokenizer_obj.tokenize(token, mode)[0].dictionary_form()
            pos = tokenizer_obj.tokenize(m, mode)[0].part_of_speech()[0]

            if pos==('名詞' or '形容詞'):
                token_result.append(m)
        except:
            pass

    # ランキングの作成
    ranking = collections.Counter(token_result).most_common()

    # トップ10が作成できる場合はランキングを返す
    if len(ranking)>=10:
        top_10 = ranking[0:10]

        # トップ10をjson形式に変換
        content = []

        for i in range(10):
            dict_data = {
              'rank': i+1,
              'word': top_10[i][0],
              'num_of_use': top_10[i][1]
            }
            content.append(dict_data)

        top_10_json = json.dumps(content, ensure_ascii=False)
        return jsonify({'content': top_10_json})

    # トップ10が作成できない場合はランキングを返さない
    not_enough = 'ランキングを作成するのに十分な会話をしていないようです。'
    top_10_json = json.dumps(not_enough, ensure_ascii=False)
    return not_enough

@app.route('/api', methods=['POST'])
def api():
    file = request.files['file']
    if file and allowed_file(file.filename):
        file.save(file.filename)
        top_10_json = word_ranking(file)
        return top_10_json
