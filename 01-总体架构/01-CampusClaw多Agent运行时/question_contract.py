"""Executable design checks for structured questions; not a Runtime implementation."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

COMMON = Path(__file__).parent / '事件契约/common.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def java_space(c):
    return c in '\t\n\v\f\r\x1c\x1d\x1e\x1f ' or ord(c) in {
        0x1680, *range(0x2000, 0x2007), *range(0x2008, 0x200B), 0x2028, 0x2029, 0x205F, 0x3000}


def stripped(s):
    start, end = 0, len(s)
    while start < end and java_space(s[start]):
        start += 1
    while end > start and java_space(s[end - 1]):
        end -= 1
    return s[start:end]


def checked_text(value, schema, normalize=False):
    require(isinstance(value, str), 'question text must be a string')
    result = stripped(value) if normalize else value
    require(bool(stripped(result)) and len(result.encode('utf-16-le')) // 2 <= schema['maxLength'],
            'question text must be nonblank and within UTF-16 limit')
    if 'pattern' in schema:
        require(re.fullmatch(schema['pattern'], result) is not None, 'invalid question id')
    return result


def contract():
    return json.loads(COMMON.read_text())['questionContract']


def normalize_questions(questions):
    schema = contract()['parameters']['properties']['questions']
    require(isinstance(questions, list) and schema['minItems'] <= len(questions) <= schema['maxItems'],
            'question batch size invalid')
    result, ids = [], set()
    props = schema['items']['properties']
    for q in questions:
        require(isinstance(q, dict) and {'id','question'} <= set(q) <= set(props), 'question fields invalid')
        qid = checked_text(q['id'], props['id'])
        require(qid not in ids, 'duplicate question id')
        ids.add(qid)
        out = {'id': qid, 'question': checked_text(q['question'], props['question'], True)}
        if 'header' in q:
            out['header'] = checked_text(q['header'], props['header'], True)
        multi = q.get('multiSelect', False)
        require(type(multi) is bool, 'multiSelect must be boolean')
        if 'options' in q:
            options, option_schema = q['options'], props['options']
            require(isinstance(options, list) and option_schema['minItems'] <= len(options) <= option_schema['maxItems'],
                    'option count invalid')
            normalized, labels = [], set()
            for option in options:
                op = option_schema['items']['properties']
                require(isinstance(option, dict) and {'label'} <= set(option) <= set(op), 'option fields invalid')
                label = checked_text(option['label'], op['label'], True)
                require(label not in labels, 'duplicate normalized option label')
                labels.add(label)
                item = {'label': label}
                if 'description' in option:
                    item['description'] = checked_text(option['description'], op['description'], True)
                normalized.append(item)
            out['options'] = normalized
        else:
            require(not multi, 'text-only question cannot enable multiSelect')
        out['multiSelect'] = multi
        result.append(out)
    return result


def validate_question_event(event):
    require(set(event) == {'eventId','type','createdAt','sourceEventId','toolCallId','questions'}, 'question event fields invalid')
    require(event['type'] == 'agent.question', 'question event type invalid')
    require(isinstance(event['toolCallId'], str) and bool(stripped(event['toolCallId'])), 'question needs tool identity')
    require(normalize_questions(event['questions']) == event['questions'], 'question snapshot must already be normalized')


def validate_answer_event(event, receipt=False):
    c = contract()['answerEvent']
    expected = set(c['required']) | ({'eventId','createdAt'} if receipt else set())
    require(set(event) == expected and event['type'] == 'user.question_answer', 'answer event fields invalid')
    checked_text(event['targetEventId'], c['properties']['targetEventId'])
    a_schema = c['properties']['answers']
    answers = event['answers']
    require(isinstance(answers, list) and a_schema['minItems'] <= len(answers) <= a_schema['maxItems'], 'answer count invalid')
    props = a_schema['items']['properties']
    ids = set()
    for item in answers:
        require(isinstance(item, dict) and {'id','selected'} <= set(item) <= set(props), 'answer fields invalid')
        qid = checked_text(item['id'], props['id'])
        require(qid not in ids, 'duplicate answer id')
        ids.add(qid)
        selected = item['selected']
        require(isinstance(selected, list) and len(selected) <= props['selected']['maxItems'], 'selected must be bounded array')
        for label in selected:
            checked_text(label, props['selected']['items'])
        require(len(selected) == len(set(selected)), 'selected labels must be unique')
        if 'custom' in item:
            custom = checked_text(item['custom'], props['custom'], True)
            if receipt:
                require(custom == item['custom'], 'receipt custom must be normalized')
        require(selected or 'custom' in item, 'empty answer is not a skip')


def normalize_answers(questions, event):
    validate_answer_event(event, receipt='eventId' in event)
    by_id = {a['id']: a for a in event['answers']}
    require(set(by_id) == {q['id'] for q in questions}, 'answers must cover the exact question set')
    result = []
    for q in questions:
        answer = by_id[q['id']]
        labels = [o['label'] for o in q.get('options', [])]
        require(set(answer['selected']) <= set(labels), 'answer selects an unknown option')
        if not q['multiSelect']:
            require(len(answer['selected']) <= 1 and not (answer['selected'] and 'custom' in answer), 'single-select conflict')
        out = {'id':q['id'], 'selected':[x for x in labels if x in answer['selected']]}
        if 'custom' in answer:
            out['custom'] = stripped(answer['custom'])
        result.append(out)
    return result


def frames(post, response_id):
    raw = next(r['bodies']['default'] for r in post['operation']['responses'] if r['id'] == response_id)
    return [json.loads(f[6:]) for f in raw.strip().split('\n\n') if f.startswith('data: ')]


def validate_question_flow(post):
    asking, answered = frames(post,'200-question-asking'), frames(post,'200-question-answered')
    require([e['type'] for e in asking] == ['user.message','agent.tool_call','agent.question','session.status_idle'], 'question order differs')
    call, question = asking[1:3]
    validate_question_event(question)
    require(call['toolName'] == 'AskUserQuestion' and not call['requiresConfirmation'], 'question is not tool permission')
    require(set(call['arguments']) == {'questions'}, 'question tool arguments invalid')
    require(question['questions'] == normalize_questions(call['arguments']['questions']) and question['toolCallId'] == call['toolCallId'], 'question differs from original call')
    require(asking[-1]['reason'] == 'confirming', 'question wait must not terminate execution')
    receipt, result = answered[:2]
    validate_answer_event(receipt,True)
    require(receipt['targetEventId'] == question['eventId'], 'answer targets another question')
    require(receipt['answers'] == normalize_answers(question['questions'], receipt), 'answer receipt is not normalized')
    require(result['type'] == 'agent.tool_result' and result['toolCallId'] == question['toolCallId']
            and result['isError'] is False and 'errorCode' not in result, 'answer result must be normal and matched')
    require(result['content'] == [{'type':'text','text':json.dumps({'answers':receipt['answers']},ensure_ascii=False,separators=(',',':'))}], 'result differs from accepted answer')
    require(all(e['sourceEventId'] == asking[0]['eventId'] for e in asking[1:]+answered[1:]), 'question changed root')
    require(not any(e['type'] in {'agent.todo_updated','session.mode_changed'} for e in asking+answered), 'plan answer must not create progress or approval')
    require(answered[-1]['reason'] == 'confirming' and any(e['type']=='agent.plan' for e in answered), 'answer continues to a separate plan review')


def validate_question_regressions(post):
    validate_question_flow(post)
    question = frames(post,'200-question-asking')[2]
    receipt = frames(post,'200-question-answered')[0]
    cases=[]
    def bad(label, value, check):
        cases.append((label,value,check))
    for key,value in [('questions',[]),('questions',question['questions']*4),('toolCallId',' '),('phase','completed')]:
        e=copy.deepcopy(question);e[key]=value;bad(key,e,validate_question_event)
    for label, mutate in [
        ('duplicate id',lambda qs: qs.append(copy.deepcopy(qs[0]))),
        ('unknown question field',lambda qs: qs[0].update(approved=True)),
        ('null question',lambda qs: qs[0].update(question=None)),
        ('blank question',lambda qs: qs[0].update(question='\u3000')),
        ('UTF16 overflow',lambda qs: qs[0].update(question='😀'*1025)),
        ('id with spaces',lambda qs: qs[0].update(id=' scope')),
        ('invalid boolean',lambda qs: qs[0].update(multiSelect='false')),
        ('null options',lambda qs: qs[0].update(options=None)),
        ('one option',lambda qs: qs[0].update(options=[{'label':'a'}])),
        ('duplicate normalized labels',lambda qs: qs[0].update(options=[{'label':'a'},{'label':' a '}]))]:
        e=copy.deepcopy(question);mutate(e['questions']);bad(label,e,validate_question_event)
    for label, mutate in [
        ('empty answers',lambda e: e.update(answers=[])),
        ('unknown field',lambda e: e.update(approved=True)),
        ('null target',lambda e: e.update(targetEventId=None)),
        ('unknown id',lambda e: e['answers'][0].update(id='other')),
        ('duplicate answer',lambda e: e['answers'].append(copy.deepcopy(e['answers'][0]))),
        ('unknown selection',lambda e: e['answers'][0].update(selected=['unknown'])),
        ('duplicate selection',lambda e: e['answers'][0].update(selected=['东区园区']*2)),
        ('single-select two choices',lambda e: e['answers'][0].update(selected=['东区园区','全部园区'])),
        ('single-select mixed custom',lambda e: e['answers'][0].update(custom='other')),
        ('null custom',lambda e: e['answers'][0].update(selected=[],custom=None)),
        ('empty skip',lambda e: e['answers'][0].update(selected=[])),
        ('blank custom',lambda e: e['answers'][0].update(selected=[],custom='\u3000')),
        ('UTF16 answer overflow',lambda e: e['answers'][0].update(selected=[],custom='😀'*2049))]:
        e=copy.deepcopy(receipt);mutate(e);bad(label,e,lambda x: normalize_answers(question['questions'],x))
    # Cross-record failures must be caught even when individual event shapes remain valid.
    for response_id, event_type, field,value in [
        ('200-question-asking','agent.question','toolCallId','wrong'),
        ('200-question-answered','user.question_answer','targetEventId','stale'),
        ('200-question-answered','agent.tool_result','toolCallId','wrong')]:
        m=copy.deepcopy(post);fs=frames(m,response_id);next(e for e in fs if e['type']==event_type)[field]=value
        next(r for r in m['operation']['responses'] if r['id']==response_id)['bodies']['default']=''.join('data: '+json.dumps(e,ensure_ascii=False)+'\n\n' for e in fs)
        bad(field,m,validate_question_flow)
    for label,value,check in cases:
        try:
            check(value)
        except ValueError:
            continue
        raise ValueError(f'question negative case accepted: {label}')
    # Positive normalization, free text, multi-select and complete batched answers.
    qs=normalize_questions([{'id':'text','question':'\u3000问题\u3000'}, {'id':'multi','question':'选项','options':[{'label':'a'},{'label':'b'}],'multiSelect':True}])
    answer={'type':'user.question_answer','targetEventId':'target','answers':[{'id':'multi','selected':['b','a'],'custom':' 补充 '},{'id':'text','selected':[],'custom':' 无法确定 '}]}
    require(normalize_answers(qs,answer)==[{'id':'text','selected':[],'custom':'无法确定'},{'id':'multi','selected':['a','b'],'custom':'补充'}], 'positive answer normalization failed')
    partial=copy.deepcopy(answer);partial['answers'].pop()
    try:
        normalize_answers(qs,partial)
    except ValueError:
        return len(cases)+1
    raise ValueError('partial answer accepted')
