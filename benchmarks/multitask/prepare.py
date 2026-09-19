"""Download public benchmark sources and freeze samples/rubrics before inference."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import tarfile
import urllib.request
import zipfile

SEED = 20260920
TWEET = 'https://raw.githubusercontent.com/cardiffnlp/tweeteval/4fbd22cd78421f05b1ecdb4fc5725bc7a7bd8f66/datasets'
BANK = 'https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/57ec275d8078af65b7731c2a98be812d844a6d6b/banking_data'
NEWS = 'https://raw.githubusercontent.com/mhjabreel/CharCnn_Keras/555590db4219b1243abb1918effd6a7425a2d75f/data/ag_news_csv'
LOG = 'https://raw.githubusercontent.com/logpai/loghub/dd61d0952749ee7963bde24220d1be5ede023033/Apache/Apache_2k.log'
TWEET_RUBRICS = {
    'sentiment': ('What sentiment does the author express in this tweet?', {
        'negative': 'An unfavorable or negative opinion or feeling.',
        'neutral': 'Neutral, factual or neither clearly positive nor negative.',
        'positive': 'A favorable or positive opinion or feeling.'}),
    'emotion': ('Which of these four emotions best describes the emotion expressed in this tweet?', {
        'anger': 'Anger, irritation, frustration or rage.', 'joy': 'Joy, happiness, pleasure or excitement.',
        'optimism': 'Optimism, hope or confidence about a positive future.', 'sadness': 'Sadness, grief, disappointment or sorrow.'}),
    'irony': ('Does the tweet communicate irony or sarcasm rather than a literal statement?', {
        'non_irony': 'The statement is intended literally, without irony or sarcasm.',
        'irony': 'The intended meaning contrasts with the literal wording, including sarcasm or ironic situations.'}),
    'offensive': ('Does this tweet contain offensive language?', {
        'non_offensive': 'Non-offensive language, with no insult, abusive language or profanity.',
        'offensive': 'An insult, threat, abusive language, vulgarity or profanity, whether targeted or untargeted.'}),
    'hate': ('Does this tweet express hate speech targeting women or immigrants?', {
        'non_hate': 'Does not express hatred, dehumanization, exclusion or violence targeting women or immigrants as a group.',
        'hate': 'Expresses hatred, dehumanization, exclusion or violence targeting women or immigrants as a group.'}),
}
# Official integer-label order; checked against each source mapping.txt below.
TWEET_LABELS = {'sentiment': ['negative', 'neutral', 'positive'], 'emotion': ['anger', 'joy', 'optimism', 'sadness'],
                'irony': ['non_irony', 'irony'], 'offensive': ['non_offensive', 'offensive'], 'hate': ['non_hate', 'hate']}


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def write_rows(path, rows):
    path.write_text(''.join(encode(row) + '\n' for row in rows), encoding='utf-8')


def prepare(root):
    cache = root / 'sources'
    cache.mkdir(parents=True, exist_ok=True)
    sources = {}
    def fetch(url, name):
        path = cache / name
        if not path.exists():
            print('Downloading', name, flush=True)
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            path.write_bytes(data)
        data = path.read_bytes()
        sources[name] = {'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
        return data

    def save(name, test, train, count, question, criteria, source_names, stratified=False, extra=None):
        folder = root / name
        folder.mkdir(exist_ok=True)
        rng = random.Random(SEED)
        if stratified:
            selected = []
            for label in sorted(criteria):
                selected.extend(rng.sample([row for row in test if row['expected'] == label], count))
            rng.shuffle(selected)
        else:
            selected = rng.sample(test, min(count, len(test)))
        assert {row['expected'] for row in selected} <= criteria.keys()
        assert len({row['id'] for row in selected}) == len(selected)
        # Content-only de-duplication between baseline training and evaluation.
        test_content = {encode(row['content']) for row in selected}
        train = [row for row in train if encode(row['content']) not in test_content]
        write_rows(folder / 'items.jsonl', [{'id': row['id'], 'content': row['content']} for row in selected])
        write_rows(folder / 'labels.jsonl', [{'id': row['id'], 'expected': row['expected']} for row in selected])
        write_rows(folder / 'train.jsonl', train)
        rubric = {'question': question, 'criteria': criteria, 'source': {'kind': 'jsonl', 'paths': ['items.jsonl']},
                  'confidence_threshold': 0.8, 'review_limit': 0, 'concurrency': 4}
        (folder / 'rubric.json').write_text(json.dumps(rubric, indent=2) + '\n', encoding='utf-8')
        manifest = {'name': name, 'seed': SEED, 'sample_items': len(selected), 'test_pool_items': len(test),
                    'baseline_train_items': len(train), 'class_counts': dict(Counter(row['expected'] for row in selected)),
                    'selection': f'{count} per class, classes sorted, then shuffle' if stratified else f'uniform sample of {len(selected)} rows',
                    'sources': {key: sources[key] for key in source_names},
                    'files_sha256': {key: hashlib.sha256((folder / key).read_bytes()).hexdigest()
                                     for key in ['items.jsonl', 'labels.jsonl', 'train.jsonl', 'rubric.json']},
                    'notes': extra or ''}
        (folder / 'dataset.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        print('Prepared', name, len(selected), 'evaluation rows;', len(train), 'baseline training rows', flush=True)

    for task, (question, criteria) in TWEET_RUBRICS.items():
        names, split_rows = [], {}
        mapping = fetch(f'{TWEET}/{task}/mapping.txt', f'tweet-{task}-mapping.txt').decode()
        print(task, 'source labels:', mapping.replace('\n', '; '), flush=True)
        for split in ['train', 'test']:
            texts_name, labels_name = f'tweet-{task}-{split}-text.txt', f'tweet-{task}-{split}-labels.txt'
            texts = fetch(f'{TWEET}/{task}/{split}_text.txt', texts_name).decode('utf-8').split('\n')
            labels = fetch(f'{TWEET}/{task}/{split}_labels.txt', labels_name).decode('utf-8').split()
            if texts[-1] == '':
                texts.pop()
            assert len(texts) == len(labels), (task, split, len(texts), len(labels))
            split_rows[split] = [{'id': f'{task}:{split}:{i+1}', 'content': text, 'expected': TWEET_LABELS[task][int(label)]}
                                 for i, (text, label) in enumerate(zip(texts, labels))]
            names.extend([texts_name, labels_name])
        names.append(f'tweet-{task}-mapping.txt')
        save(f'tweet-{task}', split_rows['test'], split_rows['train'], 500, question, criteria, names)

    classes = json.loads(fetch(f'{BANK}/categories.json', 'bank-categories.json'))
    bank = {}
    for split in ['train', 'test']:
        rows = csv.DictReader(io.StringIO(fetch(f'{BANK}/{split}.csv', f'bank-{split}.csv').decode('utf-8')))
        bank[split] = [{'id': f'banking77:{split}:{i+1}', 'content': row['text'], 'expected': row['category']} for i, row in enumerate(rows)]
    save('banking77', bank['test'], bank['train'], 10,
         'Which specific banking support intent best matches the customer message? Choose the most specific issue expressed.',
         {label: label.replace('_', ' ') for label in classes}, ['bank-categories.json', 'bank-train.csv', 'bank-test.csv'], stratified=True)

    news, mapping = {}, {'1': 'world', '2': 'sports', '3': 'business', '4': 'science_technology'}
    for split in ['train', 'test']:
        rows = csv.reader(io.StringIO(fetch(f'{NEWS}/{split}.csv', f'news-{split}.csv').decode('utf-8')))
        news[split] = [{'id': f'ag-news-{split}:{i+1}', 'content': {'title': row[1], 'description': row[2]}, 'expected': mapping[row[0]]}
                       for i, row in enumerate(rows)]
    prior = Path(__file__).resolve().parents[1] / 'ag-news-400' / 'labels.jsonl'
    prior_ids = {json.loads(line)['id'] for line in prior.read_text().split('\n') if line}
    news['test'] = [row for row in news['test'] if row['id'] not in prior_ids]
    original = json.loads((prior.parent / 'rubric.json').read_text())
    save('ag-news', news['test'], news['train'], 1000, original['question'], original['criteria'], ['news-train.csv', 'news-test.csv'],
         extra='Excludes the 400 previously evaluated AG News IDs; public data may occur in model pretraining.')

    archive = fetch('https://archive.ics.uci.edu/static/public/228/sms%2Bspam%2Bcollection.zip', 'sms.zip')
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        rows = zipped.read('SMSSpamCollection').decode('utf-8').split('\n')
    sms = []
    for i, row in enumerate(rows):
        if row.strip():
            label, content = row.split('\t', 1)
            sms.append({'id': f'sms:{i+1}', 'content': content, 'expected': label})
    rng = random.Random(SEED)
    rng.shuffle(sms)
    save('sms-spam', sms[:500], sms[500:], 500, 'Is this SMS message unsolicited spam or a legitimate personal message?',
         {'ham': 'Legitimate personal or expected communication, not unsolicited spam.',
          'spam': 'Unsolicited promotional, scam, prize, premium-rate or other spam message.'}, ['sms.zip'],
         extra='Seeded 500-row holdout because the source has no official split; exact duplicate test texts removed from baseline training.')

    lines = fetch(LOG, 'apache.log').decode('utf-8').split('\n')
    logs = []
    for i, line in enumerate(lines):
        if line.strip():
            match = re.search(r'\[(notice|error|warn|info|debug|crit|alert|emerg)\]', line)
            assert match, i
            logs.append({'id': f'apache:{i+1}', 'content': line, 'expected': match.group(1)})
    criteria = {label: f'The explicitly recorded Apache log severity is {label}.' for label in sorted({row['expected'] for row in logs})}
    rng.shuffle(logs)
    save('apache-logs', logs[:300], logs[300:], 300, 'Read the explicitly recorded severity of this Apache log entry.',
         criteria, ['apache.log'], extra='Negative control: severity is literally present in brackets; a regular expression is the correct zero-inference baseline.')

    archive = fetch('https://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz', 'imdb.tar.gz')
    imdb = {'train': [], 'test': []}
    extracted = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r|gz') as tar:
        for member in tar:
            if re.fullmatch(r'aclImdb/(train|test)/(pos|neg)/\d+_\d+\.txt', member.name):
                extracted[member.name] = tar.extractfile(member).read().decode('utf-8')
    for name in sorted(extracted):
        _, split, label, filename = name.split('/')
        # File paths contain gold sentiment and rating: never expose them to the classifier.
        identity = 'imdb:' + hashlib.sha256(f'{split}:{len(imdb[split])+1}'.encode()).hexdigest()[:20]
        imdb[split].append({'id': identity, 'content': extracted[name],
                           'expected': 'positive' if label == 'pos' else 'negative'})
    save('imdb', imdb['test'], imdb['train'], 500, 'Is the overall opinion in this movie review positive or negative?',
         {'positive': 'An overall favorable review of the movie.', 'negative': 'An overall unfavorable review of the movie.'}, ['imdb.tar.gz'],
         extra='Official test split. Neutral IDs hide the original pos/neg directory and numeric movie rating.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    prepare(args.root)
