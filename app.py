from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from sudachipy import tokenizer, dictionary
import collections
import json

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSION = 'txt'

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

def word_ranking(file):
    # トーク履歴の読み込み
    with open(file.filename) as f:
        talk = f.read()

    talk_list = talk.split()

    # トーク履歴から会話内容を抽出
    # ランキング作成用の会話内容を抽出
    talk_put_together = ''
    time_pattern = re.compile(r"\d{1,2}:\d{2}")
    week_pattern = re.compile(r"(月|火|水|木|金|土|日)曜日")
    abbr_week_pattern = re.compile(r"\((月|火|水|木|金|土|日)\)")

    for i in range(1, len(talk_list)):
        time_match = re.search(time_pattern, talk_list[i])
        week_match = re.search(week_pattern, talk_list[i-1]) or re.search(abbr_week_pattern, talk_list[i-1])

        if time_match and not(week_match):
            talk_put_together += talk_list[i-1]

    # ローディング用の会話内容を抽出
    serial_talk = []

    for i in range(1, len(talk_list)):
        time_match = re.search(time_pattern, talk_list[i])
        week_match = re.search(week_pattern, talk_list[i-1]) or re.search(abbr_week_pattern, talk_list[i-1])

        if time_match and not(week_match):
            if 'トーク履歴' in talk_list[i-2]:
                continue
            serial_talk.append([talk_list[i-2], talk_list[i-1]])
            if len(serial_talk)==10:
                break

    # 会話内容から英数字と特殊記号と除外ワードを削除
    alphanumeric_pattern = re.compile('[a-zA-Z0-9]+')
    mark_pattern = re.compile('[!"#$%&\'\\\\()*+,-./:;<=>?@[\\]^_`{|}~「」〔〕“”〈〉『』【】＆＊・（）＄＃＠。、？！｀＋￥％]')
    forbidden_pattern = re.compile(r"スタンプ|写真|動画")

    talk_put_together = alphanumeric_pattern.sub('', talk_put_together)
    cleaned_talk = mark_pattern.sub('', talk_put_together)
    cleaned_talk = forbidden_pattern.sub('', cleaned_talk)

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

    # トップ10の作成
    top_10_list = []
    serial_talk_list = []

    # トップ10＆ローディング用の会話内容をjson形式に変換
    for i in range(10):
        try:
            top_10_dict = {
              'rank': i+1,
              'word': ranking[i][0],
              'num_of_use': ranking[i][1]
            }

            serial_talk_dict = {
              'name': serial_talk[i][0],
              'talk': serial_talk[i][1]
            }
        except:
            top_10_dict = {
              'rank': i+1,
              'word': '',
              'num_of_use': ''
            }

            serial_talk_dict = {
              'name': '',
              'talk': ''
            }

        top_10_list.append(top_10_dict)
        serial_talk_list.append(serial_talk_dict)

    top_10_json = json.dumps(top_10_list, ensure_ascii=False)
    serial_talk_json = json.dumps(serial_talk_list, ensure_ascii=False)

    # トップ100の作成
    top_100_list = []

    # トップ100をjson形式に変換
    for i in range(100):
        try:
            top_100_dict = {
              'rank': i+1,
              'word': ranking[i][0],
              'num_of_use': ranking[i][1]
            }
        except:
            top_100_dict = {
              'rank': i+1,
              'word': '',
              'num_of_use': ''
            }

        top_100_list.append(top_100_dict)

    top_100_json = json.dumps(top_100_list, ensure_ascii=False)
    return jsonify({'top_10': top_10_json, 'top_100': top_100_json, 'serial_talk': serial_talk_json})

@app.route('/')
def index():
    return 'word-ranking-api'

@app.route('/api', methods=['POST'])
def api():
    file = request.files['file']
    if file and allowed_file(file.filename):
        file.save(file.filename)
        top_10_json = word_ranking(file)
        return top_10_json
