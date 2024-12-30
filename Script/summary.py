# import pandas as pd
# import numpy as np
# import nltk
# import re
# from sklearn.metrics.pairwise import cosine_similarity
# import networkx as nx
# from nltk.tokenize import sent_tokenize
# from nltk.corpus import stopwords

# nltk.download('stopwords')
# stop_words = stopwords.words('english')
# nltk.download('punkt')

# def word_vector():
#     word_embeddings = {}
#     with open('./Script/glove.6B/glove.6B.100d.txt', encoding='utf-8') as f:
#         for line in f:
#             values = line.split()
#             word = values[0]
#             coefs = np.asarray(values[1:], dtype='float32')
#             word_embeddings[word] = coefs
#     return word_embeddings

# word_embeddings = word_vector()

# def readtext(text):
#     sentences = sent_tokenize(text)
#     return sentences

# def remove_stopwords(sen):
#     sen_new = " ".join([i for i in sen if i not in stop_words])
#     return sen_new

# def preprocess(text):
#     sentences = readtext(text)
#     clean_sentences = []
#     for sentence in sentences:
#         clean = re.sub(r'[^a-zA-Z]', ' ', sentence)
#         clean = clean.lower()
#         clean = remove_stopwords(clean.split())
#         clean_sentences.append(clean)
#     return clean_sentences

# def gloveVector(clean_sentence):
#     sentence_vectors = []
#     for sentence in clean_sentence:
#         if len(sentence) != 0:
#             v = sum([word_embeddings.get(w, np.zeros((100,))) for w in sentence.split()]) / (len(sentence.split()) + 0.001)
#         else:
#             v = np.zeros((100,))
#         sentence_vectors.append(v)
#     return sentence_vectors

# def generate_similarity_score(text):
#     sentences = readtext(text)
#     clean_sentence = preprocess(text)
#     sentence_vectors = gloveVector(clean_sentence)
#     sim_mat = np.zeros([len(sentences), len(sentences)])
#     for i in range(len(sentences)):
#         for j in range(i + 1, len(sentences)):
#             sim_mat[i][j] = cosine_similarity(sentence_vectors[i].reshape(1, 100), sentence_vectors[j].reshape(1, 100))[0, 0]
#             sim_mat[j][i] = sim_mat[i][j]
#     nx_graph = nx.from_numpy_array(sim_mat)
#     scores = nx.pagerank(nx_graph)
#     ranked_sentences = sorted(((scores[i], sentences[i]) for i in range(len(sentences))), reverse=True)
#     return ranked_sentences

# def summary_generator(text):
#     result = ""  # Initialize result here
#     ranked_sentences = generate_similarity_score(text)
#     for i in range(5):
#         result += " " + ranked_sentences[i][1]
#     return result
