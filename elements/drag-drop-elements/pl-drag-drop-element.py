import prairielearn as pl
import lxml.html
import random

# Read https://prairielearn.readthedocs.io/en/latest/devElements/
# Official documentation on making custom PL


def render(element_html, data):
    if data['panel'] == 'question':
        mcq_options = []   # stores MCQ options
        question_instruction_blocks = []   # stores question instructions within the table
        html_string = ''   # html_string is the HTML we return to PL
        pl_drag_drop_element = lxml.html.fragment_fromstring(element_html)

        for html_tags in pl_drag_drop_element:
            if html_tags.tag == 'pl-answer':
                # check if <pl-answer correct=""> attribute exists
                pl.check_attribs(html_tags, required_attribs=['correct'], optional_attribs=['ranking'])
                mcq_options.append(str.strip(html_tags.text))   # store the original specified ordering of all the MCQ options
            if html_tags.tag == 'pl-info':
                question_instruction_blocks.append(str.strip(html_tags.text))

        answerName = pl.get_string_attrib(pl_drag_drop_element, 'answers-name')

        html_string = '<div class="row"><div class="column"><ul ' + f'id="{str(answerName) + str("-options")}" name="{str(answerName)}"' + 'class="connectedSortable" >'

        # check whether we need to shuffle the MCQ options
        pl.check_attribs(pl_drag_drop_element, required_attribs=['shuffle-options', 'permutation-mode', 'answers-name'], optional_attribs=[])
        isShuffle = pl.get_string_attrib(pl_drag_drop_element, 'shuffle-options')
        if isShuffle == 'true':
            # concat the two arrays so we can shuffle all the options
            random.shuffle(mcq_options)
        html_string += "<li class='ui-sortable-handle info info-fixed'>Choose from these option:</li>"
        student_previous_submission = []
        if answerName in data['submitted_answers']:
            student_previous_submission = data['submitted_answers'][answerName]['student_raw_submission']
            # the student has previously submitted something
            # we render the MCQ options the student DID NOT drag in the
            # MCQ options column
            mcq_options = list(set(mcq_options) - set(student_previous_submission))

        for mcq_options_text in mcq_options:
            # render options column
            html_string += f'<li>{mcq_options_text}</li>'

        html_string += f'</ul></div><div class="column"><ul id="{str(answerName) + str("-dropzone")}" name="{str(answerName)}" class="connectedSortable dropzone"><li class="ui-sortable-handle info info-fixed">Drag your answers below:</li>'

        for instruction_text in question_instruction_blocks:
            # render the question instruction bullet points
            html_string += f"<li class='ui-sortable-handle info info-fixed code'>{instruction_text}</li>"

        for index, mcq_options_text in enumerate(student_previous_submission):
            # render the answers column (restore the student submission)
            submission_indent = data['submitted_answers'][answerName]['student_answer_indent'][index]
            submission_indent = (int(submission_indent) * 50) + 5
            html_string += f"<li style='margin-left: {submission_indent}px;'>{mcq_options_text}</li>"
        html_string += '</ul></div></div>'

        answerName = pl.get_string_attrib(pl_drag_drop_element, 'answers-name')
        html_string += f'<input id="{str(answerName) + str("-input") }" type="text" name="{str(answerName) + str("-input") }" value=""/>'
        # html_string += f'{data}'
        return html_string

    elif data['panel'] == 'submission':
        # render the submission panel
        element = lxml.html.fragment_fromstring(element_html)
        answerName = pl.get_string_attrib(element, 'answers-name')

        if answerName in data['format_errors']:
            error = data['format_errors'][answerName]
            return f'<span style="color: #ff0000"><strong>Error: </strong> {str(error)} </span> <br><br>'

        html_string = str(data['submitted_answers'][answerName]['student_raw_submission'])
        question_notes = ''
        if answerName in data['partial_scores']:
            if 'feedback' in data['partial_scores'][answerName]:
                question_notes = str(data['partial_scores'][answerName]['feedback'])
        return f'<strong>Your answer: </strong> {str(html_string)}<br> {str(question_notes)}<br>'

    elif data['panel'] == 'answer':
        element = lxml.html.fragment_fromstring(element_html)
        answerName = pl.get_string_attrib(element, 'answers-name')
        permutationMode = pl.get_string_attrib(element, 'permutation-mode')
        permutationMode = ' in <strong> any </strong> order' if permutationMode == 'any' else 'in <strong> the specified </strong> order'
        if answerName in data['correct_answers']:
            return f"<strong>Correct answer: </strong> {data['correct_answers'][answerName]} {permutationMode} <br><br>"
        else:
            return ''

def prepare(element_html, data):
    pl_drag_drop_element = lxml.html.fragment_fromstring(element_html)
    correct_answers = []
    for html_tags in pl_drag_drop_element:
        if html_tags.tag == 'pl-answer':
            isCorrect = pl.get_string_attrib(html_tags, 'correct')
            if isCorrect.lower() == 'true':
                # add option to the correct answer array
                # answer_ordering.append(str.strip(answer_ranking))
                correct_answers.append(str.strip(html_tags.text))
    answerName = pl.get_string_attrib(pl_drag_drop_element, 'answers-name')
    data['correct_answers'][answerName] = correct_answers


def parse(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answerName = pl.get_string_attrib(element, 'answers-name')

    temp = answerName
    true_answer = data['correct_answers'][temp]
    temp += '-input'  # this is how the backend is written

    student_answer_temp = ''
    if temp in data['raw_submitted_answers']:
        student_answer_temp = data['raw_submitted_answers'][temp]

    if student_answer_temp is None:
        data['format_errors'][answerName] = 'NULL was submitted as an answer!'
        return
    elif student_answer_temp == '':
        data['format_errors'][answerName] = 'No answer was submitted.'
        return

    student_answer_temp = list(student_answer_temp.split(','))

    student_answer = []
    student_answer_indent = []
    permutationMode = pl.get_string_attrib(element, 'permutation-mode')

    student_answer_ranking = ['Question permutationMode is not "ranking"']
    for answer in student_answer_temp:
        # student answers are formatted as: {answerString}:::{indent}
        # we split the text
        answer = answer.split(':::')
        if len(answer) == 1:
            # because we already caught empty string submission above
            # failing to split the answer implies an error
            data['format_errors'][answerName] = 'Failed to parse submission: formatting is invalid! This shouldn\'t happen, contact instructor for help.'
            return

        if not str.isdigit(answer[1]) or int(answer[1]) not in list(range(0, 5)): # indent is a number in [0, 4]
            data['format_errors'][answerName] = f'Indent level {answer[1]} is invalid! Indention level must be a number between 0 or 4 inclusive.'
            return
        
        student_answer.append(answer[0])
        student_answer_indent.append(answer[1])
    del student_answer_temp
    if permutationMode.lower() == 'ranking':
        student_answer_ranking = []
        pl_drag_drop_element = lxml.html.fragment_fromstring(element_html)
        for answer in student_answer:
            e = pl_drag_drop_element.xpath(f'.//pl-answer[text()="{answer}"]')
            try:
                ranking = e[0].attrib['ranking']
            except IndexError:
                ranking = 0
            except KeyError:
                ranking = -1 # wrong answers have no ranking
            student_answer_ranking.append(ranking)
    data['submitted_answers'][answerName] = {'student_submission_ordering': student_answer_ranking, 
                                             'student_raw_submission': student_answer, 
                                             'true_answer': true_answer, 
                                             'student_answer_indent': student_answer_indent}
    if temp in data['submitted_answers']:
        del data['submitted_answers'][temp]


def grade(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answerName = pl.get_string_attrib(element, 'answers-name')

    student_answer = data['submitted_answers'][answerName]['student_raw_submission']
    true_answer = data['correct_answers'][answerName]
    permutationMode = pl.get_string_attrib(element, 'permutation-mode')

    if permutationMode == 'any':
        intersection = list(set(student_answer) & set(true_answer))
        data['partial_scores'][answerName] = {'score': float(len(intersection) / len(true_answer)), 'feedback': ''}
    elif permutationMode == 'html-order':
        if student_answer == true_answer:
            data['partial_scores'][answerName] = {'score': float(1.0), 'feedback': ''}
        else:
            data['partial_scores'][answerName] = {'score': float(0.0), 'feedback': ''}
    elif permutationMode == 'ranking':
        ranking = data['submitted_answers'][answerName]['student_submission_ordering']
        correctness = 1
        partial_credit = 0
        if len(ranking) != 0 and len(ranking) == len(true_answer):
            if ranking[0] == 1:
                partial_credit = 1  # student will at least get 1 point for getting first element correct
            for x in range(0, len(ranking) - 1):
                if int(ranking[x]) == -1:
                    correctness = 0
                    break
                if int(ranking[x]) <= int(ranking[x + 1]):
                    correctness += 1
                else:
                    correctness = 0
                    break
        else:
            correctness = 0
        correctness = max(correctness, partial_credit)
        data['partial_scores'][answerName] = {'score': float(correctness / len(true_answer)), 'feedback': ''}

def test(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answerName = pl.get_string_attrib(element, 'answers-name')
    answerNameField = answerName + '-input'

    # # incorrect and correct answer test cases
    # # this creates the EXPECTED SUBMISSION field for test cases
    if data['test_type'] == 'correct':
        temp = data['correct_answers'][answerName] # temp array to hold the correct answers
        temp = list(map(lambda x: x + ':::0', temp))
        data['raw_submitted_answers'][answerNameField] = ','.join(temp)
        data['partial_scores'][answerName] = {'score': 1, 'feedback': ''}
    elif data['test_type'] == 'incorrect':
        temp = data['correct_answers'][answerName] # temp array to hold the correct answers
        incorrect_answers = []
        for html_tags in element:
            if html_tags.tag == 'pl-answer':
                incorrect_answers.append(str.strip(html_tags.text))
        incorrect_answers = list(filter(lambda x: x not in temp, incorrect_answers))
        incorrect_answers = list(map(lambda x: x + ':::0', incorrect_answers))

        # if len(incorrect_answers) == 0:
            # raise Exception('All MCQ options are answers! I hope you know what you are doing.')

        data['raw_submitted_answers'][answerNameField] = ','.join(incorrect_answers)
        data['partial_scores'][answerName] = {'score': 0, 'feedback': ''}

    elif data['test_type'] == 'invalid':
        data['raw_submitted_answers'][answerName] = 'bad input'
        data['format_errors'][answerName] = 'format error message'
    else:
        raise Exception('invalid result: %s' % data['test_type'])