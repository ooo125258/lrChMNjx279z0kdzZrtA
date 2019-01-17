import sys
import argparse
import os
import json
import re
import string

import html
import spacy

indir = '/u/cs401/A1/data/';

abbrs = []
clitics = []
stopwords = {}

def init():
    if len(abbrs) > 0 and len(clitics) > 0:
        return
    global abbrs
    global clitics
    global stopwords

    if len(abbrs) == 0:
        abbr_filename = "./abbrev.english"
        if not os.path.isfile(abbr_filename):
            abbr_filename = "/u/cs401/Wordlists/abbrev.english"
        with open(abbr_filename) as f:
            for line in f:
                abbrs.append(line.rstrip('\n'))

    if len(clitics) == 0:
        clitics_filename = "./clitics"
        if not os.path.isfile(clitics_filename):
            clitics_filename = "/u/cs401/Wordlists/clitics"
        with open(clitics_filename) as f:
            for line in f:
                clitics.append(line.rstrip('\n'))

    if len(stopwords) == 0:
        stopwords_filename = "./StopWords"
        if not os.path.isfile(stopwords_filename):
            stopwords_filename = "/u/cs401/Wordlists/StopWords"
        with open(stopwords_filename) as f:
            for line in f:
                stopwords.append(line.rstrip('\n'))
        stopwords = set(stopwords)

def preproc1(comment, steps=range(1, 11)):
    ''' This function pre-processes a single comment

    Parameters:                                                                      
        comment : string, the body of a comment
        steps   : list of ints, each entry in this list corresponds to a preprocessing step  

    Returns:
        modComm : string, the modified comment 
    '''
    # comment = "&gt; You mean, besides being one of a handful of states known to be a State sponsor of terrorism?\
    # You mean like us in the e.g. United States supporting [Cuban terrorists](http://en.wikipedia.org/wiki/Luis_Posada_Carriles) or [Al-Qaeda](http://en.wikipedia.org/wiki/Al-Qaeda)!?? \
    # &gt;I wouldn't go so far as to say the Mr. Guardian Council... and Supreme Leader are rational - and given they are Islamists,?.?the concept of MAD does not apply.\
    # Really? Because they're Islamist they're not rational? That's why I don't like it.\n\nAny more! e.g.... alpha... clitic's dogs'. dogs'  t'challa - y'all "
    modComm = ''
    init()
    if 1 in steps:
        print('Remove all newline characters.')
        modComm = re.sub(r"(\.?)\n+", r" \1 ", comment)
        # modComm = comment.replace("\.\n", " \.")
        # modComm = comment.replace("\n", "")
    if 2 in steps:
        print('Replace HTML character codes with their ASCII equivalent.')
        modComm = html.unescape(modComm)

    if 3 in steps:
        print('Remove all URLs http/www/https')
        modComm = re.sub(r"[\(\[\{]?http[s]?://[A-Za-z0-9\/\_\.\!\#\$\%\&\\\'\*\+\,\-\:\;\=\?\@\^\|\.]+[\)\]\}]?", '',
                         modComm)
        modComm = re.sub(r"[\(\[\{]?www\.[A-Za-z0-9\/\_\.\!\#\$\%\&\\\'\*\+\,\-\:\;\=\?\@\^\|]+[\)\]\}]?", '', modComm)

    if 4 in steps:
        # skip abbr, or others

        """
        What to replace here? We are using regex!
        ... need to be together
        ?!? need to be together
        Mr., e.g. need to be together
        others split
        
        So it's the only problem for . and ', besides the second problem
        """
        # Dot here is a problem. The one dot situation will be handled later. For all "..." and "?.?" will be handled
        # It's rediculous, but ... has higher priority.
        new_modComm = re.sub(r"\.\.\.(\w|\s|$)", r" ... \1", modComm)
        new_modComm = re.sub(
            r"(\w|\s\^)(\.\.\.|[\!\#\$\%\&\\\(\)\*\+\,\-\/\:\;\<\=\>\?\@\[\]\^\_\`\{\|\}\~\.\']{2,}|[\!\#\$\%\&\\\(\)\*\+\,\-\/\:\;\<\=\>\?\@\[\]\^\_\`\{\|\}\~])(\w|\s|$)",
            r"\1 \2 \3", new_modComm)
        # Special operation for brackets
        new_modComm = re.sub(r"(\s|\^)(\[|\(|\{)", r"\1 \2 ", new_modComm)
        new_modComm = re.sub(r"(\[|\(|\{)(\s|\$|\.)", r" \1 \2", new_modComm)

        # Handle the dot problem. If find a word followed by dot, then check if it's a word in abbrs list
        def periodHandler(matched):
            lst = abbrs
            word = matched.group().strip()
            if word in abbrs:
                return " " + word + " "
            elif word[-1] == ' ' or word[-1] == '.':
                return " " + word[:len(word) - 1] + " " + "." + " "
            else:  # There is such a situation: apple.Tree e.g..Tree apple.E.g. So I choose the capital to be the identifier.
                return re.sub(r"(\w+)(\.)([A-Z])$", r" \1 \2 \3", word)

        # e.g.. , e.g. something, etc. something, something.
        # Another situation is something.\nsomething, such that it's connected!
        new_modComm = re.sub(r"(^|\s)((\w+\.)+\.?)($|\s|\w+)", periodHandler, new_modComm)
        # special case: dogs'. or t'.
        modComm = new_modComm.replace("'.", "' .")

    if 5 in steps:
        def citeHandler(matched):
            lst = clitics
            sth_matched = str(matched.group())
            word = matched.group().strip()
            for i in range(len(clitics)):
                if clitics[i] in word:
                    ret = " " + word.replace(clitics[i], " " + clitics[i] + " ") + " "
                    return ret
            ret = word.replace("'", " ' ")
            return ret

        new_modComm = re.sub(r"(^|\s)(\w*\'\w*)($|\s)", citeHandler, modComm)
        modComm = new_modComm

    if 6 in steps:
        modComm_lst = modComm.strip().split()
        nlp = spacy.load('en', disable=['parser', 'ner'])
        doc = spacy.tokens.Doc(nlp.vocab, words=modComm_lst)
        doc = nlp.tagger(doc)
        new_modComm_lst = []
        for token in doc:
            new_modComm_lst.append(token.text + "/" + token.tag_)
            # print(token.text, token.lemma_, token.pos_, token.tag_, token.dep_,
            # token.shape_, token.is_alpha, token.is_stop)        #utt = nlp(modComm)
        modComm = " ".join(new_modComm_lst)
    if 7 in steps:
        # split to list, remove if in stopwords
        new_modComm_lst = modComm.split()
        new_modComm_lst = [x for x in new_modComm_lst if x.split('/')[0] not in stopwords]
        modComm = " ".join(new_modComm_lst)
        print('TODO')
    if 8 in steps:
        #How messy it would be! As 6 and 8 are seperated, the process must be executed again!
        #I need to revert the step 6 to run nlp again!
        modComm_lst = modComm.strip().split()
        modComm_text = []
        modComm_tags = []
        if len(modComm_lst[0].split('/')) == 2:# It means the 6 is executed already
            for i in modComm_lst:
                word_split = i.split('/')
                modComm_text.append(word_split[0])
                modComm_tags.append(word_split[1])
        else:
            modComm_text = modComm_lst

        nlp = spacy.load('en', disable=['parser', 'ner'])
        doc = spacy.tokens.Doc(nlp.vocab, words=modComm_text)
        doc = nlp.tagger(doc)
        new_modComm_lst = []
        for token in doc:
            if token.lemma_[0] == '-' and token.text[0] != '-':##curcumstance to keep token
                new_modComm_lst.append(token.text)
            else:
                new_modComm_lst.append(token.lemma_)

        if len(modComm_tags) > 0:
            changed_modComm_lst = []
            for token in range(len(new_modComm_lst)):
                changed_modComm_lst.append(new_modComm_lst[i] + '/' + modComm_tags[i])
            modComm = " ".join(changed_modComm_lst)
        else:
            modComm = " ".join(new_modComm_lst)
    if 9 in steps:#4.2.4. 
        print('TODO')
        modComm_lst = modComm.strip().split()
        putative_boundaries = [False] * len(modComm_lst)

        #put putative sentence boundaries after all occurences of .?!;:
        following = False #following: move the boundary after folling quotation marks if any.
        for i in range(len(modComm_lst)):
            if re.match("[\.\?\!\;\:]", modComm_lst[i]):
                putative_boundaries[i] = True
                following = True
            elif re.match("[\'\"]", modComm_lst[i]) and putative_boundaries[i - 1]:
                putative_boundaries[i] = True
                putative_boundaries[i - 1] = False
        #Disqualify a period boundary in the following circumstances:
            #for commonly followed by a capitalized proper name

    if 10 in steps:
        modComm = modComm.lower()

    return modComm


def main(args):
    allOutput = []
    for subdir, dirs, files in os.walk(indir):
        for file in files:
            fullFile = os.path.join(subdir, file)
            print("Processing " + fullFile)

            data = json.load(open(fullFile))

            # TODO: select appropriate args.max lines
            if args.max > 10000:
                args.max = 10000
            # TODO: read those lines with something like `j = json.loads(line)`
            startpt = args.ID[0] % len(data)
            mydata = data[startpt: startpt + args.max]
            # TODO: choose to retain fields from those lines that are relevant to you
            # TODO: add a field to each selected line called 'cat' with the value of 'file' (e.g., 'Alt', 'Right', ...)
            retained_mydata = []
            for line in mydata:
                j = json.loads(line)
                newline = {}
                newline['id'] = j['id']
                newline['cat'] = file

                # TODO: process the body field (j['body']) with preproc1(...) using default for `steps` argument
                # TODO: replace the 'body' field with the processed text
                newline['body'] = preproc1(j['body'])
                retained_mydata.append(newline)
            # TODO: append the result to 'allOutput'

    fout = open(args.output, 'w')
    fout.write(json.dumps(allOutput))
    fout.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process each .')
    parser.add_argument('ID', metavar='N', type=int, nargs=1,
                        help='your student ID')
    parser.add_argument("-o", "--output", help="Directs the output to a filename of your choice", required=True)
    parser.add_argument("--max", help="The maximum number of comments to read from each file", default=10000)
    args = parser.parse_args()

    if (args.max > 200272):
        print("Error: If you want to read more than 200,272 comments per file, you have to read them all.")
        sys.exit(1)

    main(args)
