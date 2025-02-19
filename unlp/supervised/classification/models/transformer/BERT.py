# -*- coding: utf-8 -*-

"""
@Time    : 2022/2/14 6:11 下午
@Author  : hcai
@Email   : hua.cai@unidt.com
"""
import os
import sys
import shutil
import torch
import torch.nn as nn

sys.path.append(os.path.dirname(__file__))
from sutils.get_file import get_file
from bert_modeling import BertModel
from bert_tokenization import BertTokenizer

USER_DATA_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_NAME = 'config.json'

class Config(object):
    model_key_map = {
        # 谷歌预训练模型
        'bert-base-chinese': {
            'model_url': "https://huggingface.co/bert-base-chinese/resolve/main/pytorch_model.bin",
            'config_url': "https://huggingface.co/bert-base-chinese/resolve/main/config.json",
            'vocab_url': "https://huggingface.co/bert-base-chinese/resolve/main/vocab.txt"
        },
        # 哈工大预训练模型
        'chinese-bert-wwm-ext': {
            'model_url': "https://huggingface.co/hfl/chinese-bert-wwm-ext/resolve/main/pytorch_model.bin",
            'config_url': "https://huggingface.co/hfl/chinese-bert-wwm-ext/resolve/main/config.json",
            'vocab_url': "https://huggingface.co/hfl/chinese-bert-wwm-ext/resolve/main/vocab.txt"
        }
    }

    """配置参数"""
    def __init__(self, dataset, embedding=None, **kwargs):
        model_path_name = kwargs.get('model_path', 'bert-base-chinese')
        self.model_name = 'BERT'
        self.train_path = dataset + '/data/train.txt'                                # 训练集
        self.dev_path = dataset + '/data/dev.txt'                                    # 验证集
        self.test_path = dataset + '/data/test.txt'                                  # 测试集
        self.log_path = dataset + '/log/' + self.model_name
        self.class_list = [x.strip() for x in open(dataset + '/data/class.txt').readlines()] # 类别名单
        self.save_path = dataset + '/saved_dict/' + self.model_name                  # 模型训练结果
        if not os.path.isdir(self.save_path):
            os.makedirs(self.save_path)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')   # 设备

        self.require_improvement = 2000                                 # 若超过2000batch效果还没提升，则提前结束训练
        self.num_classes = len(self.class_list)                         # 类别数
        self.num_epochs = 3                                             # epoch数
        self.batch_size = 128                                           # mini-batch大小128
        self.pad_size = 32                                              # 每句话处理成的长度(短填长切)
        self.learning_rate = 5e-5                                       # 学习率
        self.bert_path = os.path.join(USER_DATA_DIR, model_path_name) if not os.path.exists(model_path_name) else model_path_name
        if os.path.exists(self.bert_path) and os.listdir(self.bert_path):
            self.bert_path = self.bert_path
        else:
            get_file(origin=list(self.model_key_map[model_path_name].values()), extract=False, untar=False,
                     cache_dir=USER_DATA_DIR, cache_subdir=model_path_name, verbose=1)
            self.bert_path = os.path.join(USER_DATA_DIR, model_path_name)
        # 实例化的时候就保存vocab.txt文件和config.json文件
        bert_token = BertTokenizer(os.path.join(self.bert_path, 'vocab.txt'))
        bert_token.save_vocabulary(self.save_path)
        if not os.path.exists(os.path.join(self.save_path, CONFIG_NAME)):
            shutil.copyfile(os.path.join(self.bert_path, CONFIG_NAME), os.path.join(self.save_path, CONFIG_NAME))
        self.tokenizer = BertTokenizer.from_pretrained(self.bert_path)
        self.hidden_size = 768


class Model(nn.Module):
    def __init__(self, config):
        super(Model, self).__init__()
        self.bert = BertModel.from_pretrained(config.bert_path)
        for param in self.bert.parameters():
            param.requires_grad = True
        self.fc = nn.Linear(config.hidden_size, config.num_classes)

    def forward(self, x):
        context = x[0]  # 输入的句子
        mask = x[2]  # 对padding部分进行mask，和句子一个size，padding部分用0表示，如：[1, 1, 1, 1, 0, 0]
        _, pooled = self.bert(context, attention_mask=mask, output_all_encoded_layers=False)
        out = self.fc(pooled)
        return out

if __name__ == '__main__':
    config = Config(dataset=os.path.join(USER_DATA_DIR, '../../data/THUCNews'))
    bert = Model(config=config)