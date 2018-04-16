from translate import Translator
from sklearn.datasets import load_files
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.naive_bayes import MultinomialNB
import re

def translator(text):
    translator = Translator(to_lang="en", from_lang="ru")
    sentcs = text.split(".")
    translated = ""
    for s in sentcs:
        sen = translator.translate(s[:500])
        sen = re.sub(r'&quot;', '"', sen)
        translated += sen
        translated += ". "
    return translated

def categorization(text, categories):

    #categories = [
    #    'talk.politics.misc',
    #    'talk.religion.misc',
    #    'talk.politics.test',
    #    'sci.electronics',
    #]
    translation = translator(text)

    train_set = load_files("train_set", description=None, categories=categories, load_content=True, decode_error='ignore', random_state=42, encoding='cp1251')

    #from sklearn.datasets import fetch_20newsgroups
    #train_set = fetch_20newsgroups(subset='train', categories=categories, shuffle=True, random_state=42)

    count_vect = CountVectorizer()
    X_train_counts = count_vect.fit_transform(train_set.data)
    X_train_counts.shape

    docs_new = [translation]
    X_new_counts = count_vect.transform(docs_new)

    tfidf_transformer = TfidfTransformer()
    X_train_tfidf = tfidf_transformer.fit_transform(X_train_counts)


    clf = MultinomialNB().fit(X_train_tfidf, train_set.target)

    X_new_tfidf = tfidf_transformer.transform(X_new_counts)
    predicted = clf.predict(X_new_tfidf)
    for doc, category in zip(docs_new, predicted):
        print('%r => %s' % (doc, train_set.target_names[category]))
    return (train_set.target_names[category])