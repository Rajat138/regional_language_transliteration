import pandas as pd
import numpy as np
import glob
from tqdm.auto import tqdm
import re
import json
import argparse
from ai4bharat.transliteration import XlitEngine

parser = argparse.ArgumentParser(description='transliteration')

parser.add_argument(
    '--filepath', 
    type=str, 
    required=True, 
    #default='file.xlsx', 
    help='Filepath of excel/csv to be translated'
)

parser.add_argument(
    '--lang', 
    type=str, 
    required=False, 
    default='hi', 
    help='regional language'
)

def transliteration(unique_words,words_dict,language):
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



args = parser.parse_args()

filename = args.filepath
language = args.lang

extension = filename.split('.')[-1]
print(extension)

# Read file with data to convert
# File should only contain columns that you want to convert/transliterate
if extension == 'xlsx':
	df_main = pd.read_excel(filename)
else:
	df_main = pd.read_csv(filename)

# Load transliteration object to ram
engine = XlitEngine(language, beam_width=4, rescore=True) #'hi' stands for Hindi

# load the json of already converted names
dict_name = f'eng_to_{language}'
if language == 'hi':
	with open (dict_name, "r") as file:
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
final_filename = filename.split('.')[0] + '_converted.' + filename.split('.')[1] 

if extension == 'xlsx':
	df_main.to_excel(final_filename, index=False)
else:
	df_main.to_csv(final_filename, index=False)
