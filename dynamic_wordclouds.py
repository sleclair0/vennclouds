from __future__ import division
import csv,sys,codecs
try:
    import ujson as json
except:
    import json



wd = './' #TODO: what do we want the wd to be?

import re
text_ex = re.compile(ur"[\w'#@]+", re.UNICODE)
text_URL_ex = re.compile(ur"http[s]{0,1}://\S+|[\w'#@]+", re.UNICODE)
#TODO: allow tokenization options
"""
def tokenize( s, as_set=False ):
    if s:
        #return text_URL_ex.findall(s)
        if as_set:
            return list(set(text_URL_ex.findall(s.strip())))
        else:
            return text_URL_ex.findall(s.strip())
    else:
        return []
"""
"""
def tokenize( s, as_set=False ):
    if s:
        #return text_URL_ex.findall(s)
        if as_set:
            return list(set(text_URL_ex.findall(s.strip())))
        else:
            return text_URL_ex.findall(s.strip())
    else:
        return []
   """
#TODO allow different striping regex options
#stripper_ex = re.compile(ur"http[s]{0,1}://\S+|[\b\W]",re.UNICODE)
stripper_ex = re.compile(ur"http[s]{0,1}://\S+|[ ,.\"!:;\-&*\(\)\[\]]",re.UNICODE)
def tokenize( s, as_set=False ):
    if s:
        if as_set:
            #return list(set(text_URL_ex.findall(s.strip())))
            return list(set(filter(None,[x.strip() for x in stripper_ex.split(s.strip())])))
        else:
            #return text_URL_ex.findall(s.strip())
            return filter(None,[x.strip() for x in stripper_ex.split(s.strip())])
    else:
        return []

def convert(s):
    try:
        return s.group(0).encode('latin1').decode('utf8')
    except:
        return s.group(0)

#TODO: use unidecode as a backoff
def normalize( s ):
    try:
        #a = unicode(s,'unicode-escape')
        a = unicode(s)
        ####a = a.encode('utf-8','replace')
        a = a.encode('utf-8')
    except UnicodeDecodeError, TypeError:
        print "problem on unicode decode:", s
        import sys
        sys.exit()
        return ""
    #return unicode(s,'unicode-escape').encode('utf-8','replace').lower()
    ####return unicode(s).encode('utf-8','replace').lower()
    s_prime = s.replace(u'\u201d','"')
    s_prime = s_prime.replace(u'\u201c','"')
    #s_prime = a = re.sub(r'[\x80-\xFF]+', convert, a)
    #s_prime = a = re.sub(r'[\x80-\xFF]+', " ", a)
    #print s_prime
    ##s_prime = re.sub(r'[\x80-\xFF]+', " ", s_prime)
    #print s_prime
    #s_prime = s_prime.replace(u'\u0xe2',' ')
    final_string = unicode(s_prime).encode('utf-8').lower()
    #print "FINAL:",final_string
    return final_string
#return s.lower().replace('-','').replace(',','').replace('.','').replace("'",'').replace('  ','')


import random as reservoir_random
reservoir_random.seed(11223344)

df = {}
def add_string_to_idf_vector(s,df=df):
    tokens = set(tokenize(normalize(s)))
    for token in tokens:
        if token in df:
            df[token] += 1
        else:
            df[token] = 1

def add_string_to_tf_vector(s,tf,examples,test_unicode_problems=True,max_examples=5):
    norm_s = normalize(s)
    if test_unicode_problems:
        try:
            a = unicode(json.dumps(norm_s).decode('utf8','replace'))
        except UnicodeDecodeError:
            print 'Unicode Problem, excluding:',norm_s
            return
    tokens = tokenize(norm_s)
            
    for index,token in enumerate(tokens):
        if token in tf:
            tf[token] += 1
        else:
            tf[token] = 1
            examples[token] = []
        #Reservoir sampling -- see Vitter 1985.
        #Fill the reservoir first, then replace each element with some probability
        if len(examples[token]) < max_examples or reservoir_random.random() < max_examples/tf[token]:
            start = index-example_window
            end = index+example_window
            ex_string = ' '.join(tokens[max(0,index-example_window):min(index+example_window,len(tokens))] )
            if start > 0:
                ex_string = '...'+ex_string
            if end < len(tokens):
                ex_string = ex_string+'...'

            #filling the reservoir
            if len(examples[token]) < max_examples:
                examples[token].append(ex_string)
            #replacing with probability
            else:
                examples[token][reservoir_random.randint(0,max_examples-1)] = ex_string

            
    return len(tokens)


#######################
# IDF vector creation #
#######################

def create_idf_vector_from_df( df, required_count=2):
    idf = {}
    for token,count in df.items():
        if count >= required_count: #Enforce that we've seen it enough
            idf[token] = 1/ count
    return idf
    

def create_idf_vector_from_docs(docs):
    df={}
    for s in docs:
        if s.strip():
            add_string_to_idf_vector(s,df=df)
    return create_idf_vector_from_df(df)
                
def create_idf_vector_from_doc_locs(doc_locs, one_doc_per_line=True, required_count=2):
    """Assumes one document per line, multiple documents allowed by default"""
    df={}
    if one_doc_per_line:
        for doc in doc_locs:
            for s in open(doc):
                if s.strip():
                    add_string_to_idf_vector(s,df=df)
    else: #One document per text file
        for doc in doc_locs:
            add_string_to_idf_vector(open(doc).read().replace('\n',''),df=df)
    return create_idf_vector_from_df(df, required_count=required_count)


def create_token_vector(tf_vector,idf_vector,examples,other_scores={}):
    """TODO: Documentation"""
    tokens = []
    for token,tf in tf_vector.items():
        idf = idf_vector.get(token,1)
        this_token = {'text':token,
                      'tf':tf,
                      'idf':idf,
                      'examples':examples.get(token,[])}
        for score_name,token_scores in other_scores.items():
            if token in token_scores:
                this_token[score_name] = token_scores[token]
        tokens.append(this_token)
    print "TOKENS:",len(tokens)
    return tokens
    

##############################
# Dynamic Wordcloud creation #
##############################

def create_dynamic_wordclouds(input_locs, idf, output_loc, from_text_files=True, max_examples=5, dataset_names=[]):
    """
    TODO:Documentation and usage instructions needed
    """
    dataset = []
    
    for index,input_loc in enumerate(input_locs):
        if not from_text_files:
            dataset_name = dataset_names[index]
            print "Encoding",dataset_name
        else:
            dataset_name = input_loc.split('/')[-1].split('.')[0]
            print "Encoding",input_loc,'as',dataset_name

        if from_text_files:
            IN = open(input_loc)
        else:
            IN = input_loc
        
        tf = {}
        examples = {}
        num_docs = 0
        for doc in IN:
            add_string_to_tf_vector(doc, tf, examples, max_examples=max_examples)
            num_docs += 1

        #Normalizing by tokens works way better than normalizing by documents -- very sensitive to this.
        this_data = {'name':dataset_name,
                     'tf':tf,
                     'examples':examples,
                     'num_docs':num_docs}
        dataset.append(this_data)

    #Clean up TF vectors
    def remove_token(token):
        for d in dataset:
            if token in d['tf']: del d['tf'][token]
            if token in d['examples']: del d['examples'][token]
    def count_token_occurences(token):
        occurences = 0
        for d in dataset:
            occurences += d['tf'].get(token,0)
            #if token in d['tf']: occurences += d['tf'][token]
        return occurences

    #Amass all tokens
    all_tokens = set([])
    for d in dataset:
        all_tokens = all_tokens.union(set(d['tf'].keys()))
        
    #Remove all tokens that don't occur often enough
    for token in all_tokens:
        if count_token_occurences(token) < 3: #HARDCODE
            remove_token(token)
        
    #Replace TF and Examples with the full encoded dataset
    for d in dataset:
        d['tokens'] = create_token_vector(d['tf'],idf,d['examples'])
        d['num_tokens'] = sum(d['tf'].values()) #must do this after normalization occurs
        del d['tf']
        del d['examples']
    
    try:
        print 'dumping data'
        jsoned_data = unicode(json.dumps(dataset).decode('utf8','replace'))
        print 'succeeded without unicode errors'
    except UnicodeDecodeError:
        print "Unicode problem, trying to diagnose..."
        #TODO: Refactor to deal with unicode failures
        print "This portion of the code has not been refactored yet... failing."
        import sys
        sys.exit()
        for i,te in enumerate(red_examples.items()):
            term,examples = te
            try:
                a = unicode(json.dumps(term).decode('utf8', 'replace'))
                a = unicode(json.dumps(examples).decode('utf8', 'replace'))
            except UnicodeDecodeError:
                print 'Red:', i
                if term in red_raw[0]:
                    del red_raw[0][term]
                if term in red_raw[2]:
                    del red_raw[2][term]
                if term in red_raw[3]:
                    del red_raw[3][term]
        for i,te in enumerate(blue_examples.items()):
            term,examples = te
            try:
                a = unicode(json.dumps(term).decode('utf8', 'replace'))
                a = unicode(json.dumps(examples).decode('utf8', 'replace'))
            except UnicodeDecodeError:
                print 'Blue:', i
                if term in blue_raw[0]:
                    del blue_raw[0][term]
                if term in blue_raw[2]:
                    del blue_raw[2][term]
                if term in blue_raw[3]:
                    del blue_raw[3][term]
        trimmed_idf = {}
        for token in set(blue_tf.keys() + red_tf.keys()):
            if type(token) != type('a'):
                print "nonstring token:", token
            elif token in idf:
                trimmed_idf[token] = idf[token]

    template_loc = wd+'venncloud_template.html'
    parameter_anchor = '[[[PARAMETERS_GO_HERE]]]'

    OUT = codecs.open(output_loc,'w','utf8')
    html_template =  open(template_loc).read()
    html_pre,html_post = html_template.split(parameter_anchor)

    

    def write_arbitrarily_large_data(dat,OUT):
        index = 0
        while index < len(dat):
            OUT.write(dat[index:index+1000])
            index += 1000
    
    OUT.write(html_pre)
    OUT.write('datasets=')
    write_arbitrarily_large_data(jsoned_data,OUT)
    OUT.write(';\n')
    OUT.write(html_post)




if __name__ == '__main__':
    """
    Run this standalone to generate an encapsulated html file (but we still require the files in `offline_source' to run properly).
    For usage instructions: python deltawc_from_text_files.py -h
    """
    reload(sys)
    sys.setdefaultencoding('utf-8')
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stdout.encoding = 'utf-8'

    try:
        import argparse
    except: # IF you don't have argparse installed (e.g. python 2.6)
        from optparse import OptionParser
        usage = """ dynamic_wordclouds.py [-h] [--output OUTPUT] [--idf IDF]
                                     [--examples EXAMPLES] [--window WINDOW]
                                     N [N ...]
                                                                  """
        parser = OptionParser(usage=usage)
        parser.add_option('--output',dest='output',action='store',help='Where the output html file should be written.',default='generated_wordcloud.html')
        parser.add_option('--idf',dest='idf',action='store',help='Location of an idf vector to be used, as a JSON file of a python dictionary -- see `create_idf_vector.py` to make one. If this argument is omitted, we will generate the idf vector from the red and blue documents.',default=None)
        parser.add_option('--examples',dest='examples',action='store',help='Number of examples of each word to store.',default=5)
        parser.add_option('--window',dest='window',action='store',help='Window size on each side for each example, in number of tokens.',default=5)

        (options,args) = parser.parse_args()
        input_locs = args
        output_loc = options.output
        idf_loc = options.idf
        num_examples = int(options.examples)
        example_window = int(options.window)

    else:
        parser = argparse.ArgumentParser(description='Create a Venncloud html file.')
        parser.add_argument('--output',action='store',help='Where the output html file should be written.',default='generated_wordcloud.html')
        parser.add_argument('--idf',action='store',help='Location of an idf vector to be used, as a JSON file of a python dictionary -- see `create_idf_vector.py` to make one. If this argument is omitted, we will generate the idf vector from the red and blue documents.',default=None)
        parser.add_argument('--examples',action='store',help='Number of examples of each word to store.',default=5)
        parser.add_argument('--window',action='store',help='Window size on each side for each example, in number of tokens.',default=5)
        parser.add_argument('documents', metavar='N', nargs='+',
                            help='Location of the documents for the datasets to be loaded -- plain text, 1 document per line.')

        
        args = vars(parser.parse_args())
        input_locs = args['documents']
        output_loc = args['output']
        idf_loc = args['idf']
        num_examples = int(args['examples'])
        example_window = int(args['window'])
        

        

    if len(input_locs) < 1:
        print "Not enough files specified -- run this file with `-h' argument to see the help message."
        print "You must specify either a set of black documents [for a single wordcloud] or BOTH a red and blue set of documents [for a delta wordcloud]."
        import sys
        sys.exit()




    #Load the IDF vector

    idf = {}
    if idf_loc: #Load the idf vector, if precomputed
        import json
        idf = json.load(open(idf_loc))
    else: #Create the idf vector from the existing docs
        alldocs = []
        for loc in input_locs:
            alldocs += open(loc).readlines()
        idf = create_idf_vector_from_docs( alldocs )

    create_dynamic_wordclouds(input_locs,idf,output_loc,max_examples=num_examples)



