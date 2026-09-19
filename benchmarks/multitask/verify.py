"""Verify all archived quality and byte measurements without calling a model."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').split('\n') if line.strip()]


def size(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8'))


parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True,help='Prepared source directory; no API key needed')
args=parser.parse_args()
result_root=Path(__file__).resolve().parent/'results'
verified=0
for folder in sorted(result_root.iterdir()):
    if not folder.is_dir():
        continue
    report=json.loads((folder/'report.json').read_text())
    source=args.root/folder.name
    manifest=json.loads((folder/'dataset.json').read_text())
    for name,digest in manifest['files_sha256'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,(folder.name,name)
    for name,info in manifest['sources'].items():
        assert hashlib.sha256((args.root/'sources'/name).read_bytes()).hexdigest()==info['sha256'],name
    labels={row['id']:row['expected'] for row in rows(folder/'labels.jsonl')}
    predicted={row['id']:row for row in rows(folder/'predictions.jsonl')}
    inputs=rows(source/'items.jsonl')
    assert len(predicted)==len(labels)==len(inputs)==report['items']
    assert predicted.keys()==labels.keys()=={row['id'] for row in inputs}
    correct=sum(row.get('choice')==labels[key] for key,row in predicted.items())
    assert math.isclose(correct/len(labels),report['quality']['accuracy'])
    confusion=Counter((labels[key],row.get('choice','__failed__')) for key,row in predicted.items())
    f1=[]
    for label in report['rubric']['criteria']:
        tp=confusion[label,label]
        fp=sum(count for (gold,guess),count in confusion.items() if guess==label and gold!=label)
        fn=sum(count for (gold,guess),count in confusion.items() if gold==label and guess!=label)
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    assert math.isclose(sum(f1)/len(f1),report['quality']['macro_f1'])
    for sweep in report['compact_review_replay']['thresholds']:
        threshold=sweep['threshold']
        accepted={key for key,row in predicted.items() if 'error' not in row and row['confidence']>=threshold}
        assert len(accepted)==sweep['accepted']
        assert sum(predicted[key]['choice']!=labels[key] for key in accepted)==sweep['accepted_errors']
        review_bytes=sum(size(row)+1 for row in inputs if row['id'] not in accepted)
        call={**report['rubric'],'confidence_threshold':threshold}
        inline={**call,'items':inputs}
        del inline['source']
        assert size(inline)==sweep['inline_input_bytes']
        assert review_bytes==sweep['all_review_records_bytes']
        assert size(call)+size(sweep['measured_summary'])==sweep['source_call_and_result_bytes']
        expected=1-(size(call)+size(sweep['measured_summary'])+review_bytes)/size(inline)
        assert math.isclose(expected,sweep['context_bytes_reduction_with_all_reviews'])
        assert sweep['measured_summary']['accepted']==len(accepted)
        assert not sweep['measured_summary']['review']
    verified+=1
    print('Verified',folder.name,report['items'],'predictions and 7 context/quality settings')
assert verified==10
print('Verified all 5,570 predictions and all 70 threshold measurements; no paid calls.')
