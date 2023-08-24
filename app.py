import gradio as gr
import subprocess
import os
import time
import pandas as pd
import numpy as np
import glob
from tqdm.auto import tqdm
import re
import json
import argparse
import hin_to_eng
from hin_to_eng import hin_to_eng
from ai4bharat.transliteration import XlitEngine
from huggingface_hub import hf_hub_download, login
login(token='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')


def transliteration(unique_words,words_dict,language,engine):
    converted_words = []
    for i in tqdm(unique_words):
        try:
            converted_words.append(words_dict[i][0])
            continue
        except:
            pass
        i = i + ' '
        temp = ''
        converted_words_temp = ''
        for letter in i: #check each letter if it is an alphabet
            if(letter.isalpha()):
                temp = temp + letter #string till we find alphabet
            else:
                try:
                    try:
                        converted_words_temp = converted_words_temp + words_dict[temp.strip()][0] + str(letter)
                    except:
                        #word not found in words_dict
                        temp_eng2lang = engine.translit_word(temp.strip(), topk=1)
                        words_dict[temp.strip()] = [temp_eng2lang[language][0].replace('\u200c','')] # add word to dictinoary 
                        converted_words_temp = converted_words_temp + words_dict[temp.strip()][0] + str(letter)
                except:
                    #exceptional case: leave the word as it is
                    converted_words_temp = converted_words_temp + str(letter)
                temp = ''
        converted_words.append(converted_words_temp.strip())
    return converted_words

def find_unique_words(df_main):
  # collecting words to translate (to be fed into transliteration model)
  words = []
  for i in tqdm(df_main.columns): #iterating on columns
      i = str(i)
      df_temp = df_main[df_main[i].notnull()][[i]].drop_duplicates() #drop duplicate rows
      df_temp[i] = df_temp[i].apply(lambda x:str(x).lower().strip().split(' ')) #converting every word to lower and removing spaces
      df_temp = df_temp.explode([i]) # converting list to rows
      words.append(df_temp[i].unique().tolist()) # taking only unique from the column

  unique_words = list(set([i for sublist in words for i in sublist]))
  return unique_words


engine = None
language1 = None
def load_model_to_ram(language):
  global engine
  global language1

  if engine is not None and language1 == language:
    return(engine)

  elif engine is not None or language != language1:
    language1 = language
    engine = XlitEngine(language, beam_width=4, rescore=True)
    return(engine)

  else:
    return(None)

def transliteration_op(files,language):
  # Load transliteration object to ram if not already exists
  engine = load_model_to_ram(language)
  #language = 'hi'
  file_path = files.name

  extension = file_path.split('.')[-1]

  if language == 'eng':
      df_main = pd.read_excel(file_path)
      df_main_copy = df_main.copy()
      df_main = hin_to_eng(filepath)
      final_filename = filename.split('.')[0] + '_converted.' + filename.split('.')[1]
      df_main.to_excel(final_filename, index=False)
      return final_filename, df_main_copy.head(), df_main.head()

  # Read file with data to convert
  # File should only contain columns that you want to convert/transliterate

  if extension == 'xlsx':
    df_main = pd.read_excel(file_path)
    df_main_copy = df_main.copy()
  else:
    df_main = pd.read_csv(file_path)
    df_main_copy = df_main.copy()

  # load the json of already converted names
  dict_name = f'eng_to_{language}.json'
  if os.path.exists(dict_name):
    with open ('eng_to_hin.json', "r") as file:
        words_dict = json.load(file)
  else:
    words_dict = {}
  
  unique_words = find_unique_words(df_main)

  converted_words = transliteration(unique_words,words_dict,language,engine)
  converted_words_dict = dict(zip(unique_words, converted_words))

  # Updating the original dataframe with transliterated columns
  for i in tqdm(df_main.columns):
      df_main[str(i) + '_converted'] = df_main[str(i)].apply(lambda x:np.nan if(x!=x) else ' '.join([converted_words_dict[i] for i in str(x).lower().strip().split(' ')]))

  # overwrite the base_dictionary
  with open(dict_name, "w") as outfile:
      json.dump(words_dict, outfile)

  # save converted file
  filename = file_path.split('/')[-1]
  final_filename = filename.split('.')[0] + '_converted.' + filename.split('.')[1] 

  if extension == 'xlsx':
    df_main.to_excel(final_filename, index=False)
  else:
    df_main.to_csv(final_filename, index=False)

  return final_filename, df_main_copy.head(), df_main.head()

def same_auth(username, password):
    #global user
    #global pwd
    hf_hub_download(repo_id="tttarun/auth_database", repo_type = 'dataset',filename = 'credentials_transliteration.json',local_dir = 'credentials')
    with open('credentials/credentials_transliteration.json', 'r') as fp:
        user_dict = json.load(fp)

    user = username
    pwd = password
    
    if user in user_dict.keys():
        if user_dict[user] == pwd:
            return True
        else:
            return False
    else:
        return False

def clear():
  return None,None,None,None


with gr.Blocks() as demo:
  with gr.Tab("Transliteration"):
    with gr.Row().style(equal_height=True):
          with gr.Column(scale=1):
              gr.Markdown(
                  """
                  # `Transliteration English to Regional language`
                  ### `1. Choose the regional language to be transliterated in`
                  ### `2. Input excel/csv file to be transliterated` 
                  ### `3. Click upload file`
                  ### `4. English ko vanakkam !!!`
                  """
              )
    with gr.Row().style(equal_height=True):
          with gr.Column():
              with gr.Box():
                lang = gr.Dropdown(['hi','eng'],label="Select transliteration language (for now Hindi)")
                upload_button = gr.UploadButton(file_types=[".xlsx",".csv"])
                df_input = gr.Dataframe()

          with gr.Column():
              with gr.Box():
                file_output = gr.File()
                df_output = gr.Dataframe()
                with gr.Row():
                  clear_btn = gr.Button("Clear")
          upload_button.upload(transliteration_op, [upload_button, lang], [file_output,df_input,df_output])
          clear_btn.click(clear, None, [lang,file_output,df_input,df_output])

demo.queue(concurrency_count=50).launch(enable_queue=True,auth=same_auth)
