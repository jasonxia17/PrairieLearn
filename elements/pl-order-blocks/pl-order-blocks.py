import prairielearn as pl
import lxml.html
import random
import chevron
import base64
import os
import json

PL_ANSWER_CORRECTNESS_DEFAULT = True
PL_ANSWER_INDENT_DEFAULT = '-1'
CHECK_INDENTION_DEFAULT = False
SHUFFLE_SOURCE_BLOCKS_DEFAULT = False
GRADING_METHOD_DEFAULT = 'ordered'
MIN_INCORRECT_DEFAULT = None
MAX_INCORRECT_DEFAULT = None
SOURCE_HEADER_DEFAULT = 'Drag from here:'
SOLUTION_HEADER_DEFAULT = 'Construct your solution here:'


def render_html_color(score):
    # used to render the correct color depending on student score
    if score == 0:
        return 'badge-danger'
    elif score == 1.0:
        return 'badge-success'
    else:
        return 'badge-warning'


def get_all_answer(submitted_blocks, block_indents, leading_code, trailing_code):
    if len(submitted_blocks) == 0:
        return ''
    answer_code = ''
    for index, answer in enumerate(submitted_blocks):
        indent = int(block_indents[index])
        answer_code += ('    ' * indent) + answer + '\n'
    answer_code = leading_code + '\n' + answer_code + trailing_code + '\n'
    return answer_code


def prepare(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)

    pl.check_attribs(element,
                     required_attribs=['answers-name'],
                     optional_attribs=['shuffle-options',
                                       'grading-method',
                                       'check-indentation',
                                       'header-left-column',
                                       'header-right-column',
                                       'file-name',
                                       'leading-code',
                                       'trailing-code',
                                       'solution-placement',
                                       'max-incorrect',
                                       'min-incorrect',
                                       'weight'])

    answer_name = pl.get_string_attrib(element, 'answers-name')

    mcq_options = []
    html_ordering = []
    correct_answers = []
    correct_answers_indent = []
    correct_answers_ranking = []
    incorrect_answers = []

    for html_tags in element:  # iterate through the tags inside pl-order-blocks, should be <pl-answer> tags
        if html_tags.tag == 'pl-answer':
            # correct attribute is not strictly required, as the attribute is irrelevant for autograded questions
            pl.check_attribs(html_tags, required_attribs=[], optional_attribs=['correct', 'ranking', 'indent'])

            isCorrect = pl.get_boolean_attrib(html_tags, 'correct', PL_ANSWER_CORRECTNESS_DEFAULT)
            answerIndent = pl.get_string_attrib(html_tags, 'indent', PL_ANSWER_INDENT_DEFAULT)  # get answer indent, and default to -1 (indent level ignored)
            if isCorrect is True:
                # add option to the correct answer array, along with the correct required indent
                if pl.get_string_attrib(html_tags, 'ranking', '') != '':
                    ranking = pl.get_string_attrib(html_tags, 'ranking')
                    try:
                        ranking = int(ranking) - 1
                    except ValueError:
                        raise Exception('Ranking specified in <pl-answer> is not a number.')
                    correct_answers_ranking.append(ranking)
                correct_answers.append(html_tags.text)
                correct_answers_indent.append(answerIndent)
            else:
                incorrect_answers.append(html_tags.text)
            html_ordering.append(html_tags.text)
        else:
            raise Exception('Tags nested inside <pl-order-blocks> must be <pl-answer>.')

    grading_method = pl.get_string_attrib(element, 'grading-method', GRADING_METHOD_DEFAULT)
    accepted_grading_method = ['ordered', 'unordered', 'ranking', 'external']

    if grading_method not in accepted_grading_method:
        raise Exception('The grading-method attribute must be one of the following: ' + accepted_grading_method)

    if pl.get_string_attrib(element, 'grading-method', GRADING_METHOD_DEFAULT) != 'external' and len(correct_answers) == 0:
        raise Exception('There are no correct answers specified for this question.')

    if (correct_answers_ranking != sorted(correct_answers_ranking)):
        # sort correct answers by indices specified in corect_answers_ranking
        correct_answers = [x for _, x in sorted(zip(correct_answers_ranking, correct_answers))]

    min_incorrect = pl.get_integer_attrib(element, 'min-incorrect', MIN_INCORRECT_DEFAULT)
    max_incorrect = pl.get_integer_attrib(element, 'max-incorrect', MAX_INCORRECT_DEFAULT)

    if ((min_incorrect is None) & (max_incorrect is None)):
        mcq_options = correct_answers + incorrect_answers
    else:
        # Setting default for min-correct and checking for correct interval
        if min_incorrect is None:
            min_incorrect = 1
        else:
            if min_incorrect > len(incorrect_answers):
                raise Exception('min-incorrect must be smaller than the number of given distractors.')
        # Setting default for max-correct and checking for correct interval
        if max_incorrect is None:
            max_incorrect = len(incorrect_answers)
        else:
            if max_incorrect > len(incorrect_answers):
                raise Exception('max-incorrect must be smaller than the number of given distractors.')
        if min_incorrect > max_incorrect:
            raise Exception('min-incorrect must be smaller than max-incorrect.')
        incorrect_answers_count = random.randint(min_incorrect, max_incorrect)
        mcq_options = correct_answers + random.sample(incorrect_answers, incorrect_answers_count)

    is_shuffle = pl.get_boolean_attrib(element, 'shuffle-options', SHUFFLE_SOURCE_BLOCKS_DEFAULT)  # default to FALSE, no shuffling unless otherwise specified

    if is_shuffle is True:
        random.shuffle(mcq_options)
    else:
        mcq_options = html_ordering

    data['params'][answer_name] = mcq_options
    data['correct_answers'][answer_name] = {'correct_answers': correct_answers,
                                            'correct_answers_indent': correct_answers_indent}


def render(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answer_name = pl.get_string_attrib(element, 'answers-name')

    if data['panel'] == 'question':
        mcq_options = []   # stores MCQ options
        student_previous_submission = []
        submission_indent = []

        for html_tags in element:
            if html_tags.tag == 'pl-answer':
                mcq_options.append(html_tags.text)   # store the original specified ordering of all the MCQ options

        answer_name = pl.get_string_attrib(element, 'answers-name')
        header_left_column = pl.get_string_attrib(element, 'header-left-column', SOURCE_HEADER_DEFAULT)
        header_right_column = pl.get_string_attrib(element, 'header-right-column', SOLUTION_HEADER_DEFAULT)

        student_submission_dict_list = []

        mcq_options = data['params'][answer_name]

        if answer_name in data['submitted_answers']:
            student_previous_submission = data['submitted_answers'][answer_name]['student_raw_submission']
            mcq_options = list(set(mcq_options) - set(student_previous_submission))

        for index, mcq_options_text in enumerate(student_previous_submission):
            # render the answers column (restore the student submission)
            submission_indent = data['submitted_answers'][answer_name]['student_answer_indent'][index]
            submission_indent = (int(submission_indent) * 50) + 10
            temp = {'text': mcq_options_text, 'indent': submission_indent}
            student_submission_dict_list.append(dict(temp))

        dropzone_layout = pl.get_string_attrib(element, 'solution-placement', 'horizontalLayout')

        html_params = {
            'question': True,
            'answer_name': answer_name,
            'options': mcq_options,
            'header-left-column': header_left_column,
            'header-right-column': header_right_column,
            'submission_dict': student_submission_dict_list,
            'dropzone_layout': 'bottom' if dropzone_layout == 'bottom' else 'right'
        }

        with open('pl-order-blocks.mustache', 'r', encoding='utf-8') as f:
            html = chevron.render(f, html_params)
        return html

    elif data['panel'] == 'submission':
        if pl.get_string_attrib(element, 'grading-method', 'ordered') == 'external':
            return ''
        # render the submission panel
        uuid = pl.get_uuid()
        student_submission = ''
        color = 'badge-danger'
        score = 0
        feedback = None

        if answer_name in data['submitted_answers']:
            student_submission = data['submitted_answers'][answer_name]['student_raw_submission']
        if answer_name in data['partial_scores']:
            color = render_html_color(data['partial_scores'][answer_name]['score'])
            score = data['partial_scores'][answer_name]['score'] * 100
            feedback = data['partial_scores'][answer_name]['feedback']

        html_params = {
            'submission': True,
            'uuid': uuid,
            'parse-error': data['format_errors'].get(answer_name, None),
            'student_submission': pretty_print(student_submission),
            'color': color,
            'score': score,
            'perfect_score': True if score == 100 else None,
            'feedback': feedback
        }

        # Finally, render the HTML
        with open('pl-order-blocks.mustache', 'r', encoding='utf-8') as f:
            html = chevron.render(f, html_params)
        return html

    elif data['panel'] == 'answer':
        if pl.get_string_attrib(element, 'grading-method', 'ordered') == 'external':
            try:
                base_path = data['options']['question_path']
                file_lead_path = os.path.join(base_path, 'tests/ans.py')
                with open(file_lead_path, 'r') as file:
                    solution_file = file.read()
                return f'<pl-code language="python">{solution_file}</pl-code>'
            except FileNotFoundError:
                return 'The reference solution is not provided for this question.'

        grading_mode = pl.get_string_attrib(element, 'grading-method', 'ordered')
        grading_mode = 'in any order' if grading_mode == 'unordered' else 'in the specified order'

        check_indentation = pl.get_boolean_attrib(element, 'check-indentation', False)
        check_indentation = ', with correct indentation' if check_indentation is True else ''

        if answer_name in data['correct_answers']:
            html_params = {
                'true_answer': True,
                'question_solution': pretty_print(data['correct_answers'][answer_name]['correct_answers']),
                'grading_mode': grading_mode,
                'check_indentation': check_indentation
            }
            with open('pl-order-blocks.mustache', 'r', encoding='utf-8') as f:
                html = chevron.render(f, html_params)
            return html
        else:
            return ''


def pretty_print(array):
    if array is None:
        return None
    pretty_print_answer = []
    for text in array:
        temp = {'text': text}
        pretty_print_answer.append(dict(temp))
    return pretty_print_answer


def parse(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answer_name = pl.get_string_attrib(element, 'answers-name')

    temp = answer_name
    temp += '-input'
    # the answer_name textfields that raw-submitted-answer reads from
    # have '-input' appended to their name attribute

    student_answer_temp = ''
    if temp in data['raw_submitted_answers']:
        student_answer_temp = data['raw_submitted_answers'][temp]

    if student_answer_temp is None:
        data['format_errors'][answer_name] = 'NULL was submitted as an answer.'
        return
    elif student_answer_temp == '':
        data['format_errors'][answer_name] = 'No answer was submitted.'
        return

    student_answer = []
    student_answer_indent = []
    grading_mode = pl.get_string_attrib(element, 'grading-method', GRADING_METHOD_DEFAULT)

    student_answer_ranking = ['Question grading_mode is not "ranking"']

    student_answer_temp = json.loads(student_answer_temp)

    student_answer = student_answer_temp['answers']
    student_answer_indent = student_answer_temp['answer_indent']

    if grading_mode.lower() == 'ranking':
        student_answer_ranking = []
        pl_drag_drop_element = lxml.html.fragment_fromstring(element_html)
        for answer in student_answer:
            e = pl_drag_drop_element.xpath(f'.//pl-answer[text()="{answer}"]')
            isCorrect = pl.get_boolean_attrib(e[0], 'correct', PL_ANSWER_CORRECTNESS_DEFAULT)  # default correctness to True
            if isCorrect:
                ranking = pl.get_integer_attrib(e[0], 'ranking', 0)
            else:
                ranking = -1   # wrong answers have no ranking
            student_answer_ranking.append(ranking)

    if pl.get_string_attrib(element, 'grading-method', 'ordered') == 'external':
        file_name = pl.get_string_attrib(element, 'file-name', 'user_code.py')
        leading_code = pl.get_string_attrib(element, 'leading-code', None)
        trailing_code = pl.get_string_attrib(element, 'trailing-code', None)
        base_path = data['options']['question_path']

        if leading_code is not None:
            file_lead_path = os.path.join(base_path, leading_code)
            with open(file_lead_path, 'r') as file:
                leadingnew_code = file.read()
        if trailing_code is not None:
            file_trail_path = os.path.join(base_path, trailing_code)
            with open(file_trail_path, 'r') as file:
                trailnewx_code = file.read()

        if file_name is not None:
            if leading_code is not None and trailing_code is not None:
                file_data = get_all_answer(student_answer, student_answer_indent, leadingnew_code, trailnewx_code)
            elif leading_code is None and trailing_code is not None:
                file_data = get_all_answer(student_answer, student_answer_indent, '', trailnewx_code)
            elif leading_code is not None and trailing_code is None:
                file_data = get_all_answer(student_answer, student_answer_indent, leadingnew_code, '')
            else:
                file_data = get_all_answer(student_answer, student_answer_indent, '', '')
            if len(file_data) == 0:
                data['format_errors']['_files'] = 'The submitted file was empty.'
            else:
                data['submitted_answers']['_files'] = [{'name': file_name, 'contents': base64.b64encode(file_data.encode('utf-8')).decode('utf-8')}]

    data['submitted_answers'][answer_name] = {'student_submission_ordering': student_answer_ranking,
                                              'student_raw_submission': student_answer,
                                              'student_answer_indent': student_answer_indent}
    if temp in data['submitted_answers']:
        del data['submitted_answers'][temp]


def grade(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answer_name = pl.get_string_attrib(element, 'answers-name')

    student_answer = data['submitted_answers'][answer_name]['student_raw_submission']
    student_answer_indent = data['submitted_answers'][answer_name]['student_answer_indent']
    grading_mode = pl.get_string_attrib(element, 'grading-method', GRADING_METHOD_DEFAULT)
    true_answer = data['correct_answers'][answer_name]['correct_answers']
    true_answer_indent = data['correct_answers'][answer_name]['correct_answers_indent']

    indent_score = 0
    final_score = 0
    feedback = ''

    if len(student_answer) == 0:
        data['format_errors'][answer_name] = 'Your submitted answer was empty.'
        return

    if grading_mode == 'unordered':
        intersection = list(set(student_answer) & set(true_answer))
        incorrect_answers = list(set(student_answer) - set(true_answer))
        final_score = float((len(intersection) - len(incorrect_answers)) / len(true_answer))
        final_score = max(0.0, final_score)  # scores cannot be below 0
    elif grading_mode == 'ordered':
        final_score = 1.0 if student_answer == true_answer else 0.0
    elif grading_mode == 'ranking':
        ranking = data['submitted_answers'][answer_name]['student_submission_ordering']
        correctness = 1 + ranking.count(0)
        partial_credit = 0
        if len(ranking) != 0 and len(ranking) == len(true_answer):
            ranking = list(filter(lambda x: x != 0, ranking))
            if ranking[0] == 1:
                partial_credit = 1  # student will at least get 1 point for getting first element correct
            for x in range(0, len(ranking) - 1):
                if int(ranking[x]) == int(ranking[x + 1]) or int(ranking[x]) + 1 == int(ranking[x + 1]):
                    correctness += 1
        else:
            correctness = 0
        correctness = max(correctness, partial_credit)
        final_score = float(correctness / len(true_answer))

    check_indentation = pl.get_boolean_attrib(element, 'check-indentation', CHECK_INDENTION_DEFAULT)
    answer_weight = pl.get_integer_attrib(element, 'weight', 1)
    # check indents, and apply penalty if applicable
    if check_indentation is True:
        for i, indent in enumerate(student_answer_indent):
            if indent == true_answer_indent[i] or true_answer_indent[i] == '-1':
                indent_score += 1
        final_score = final_score * (indent_score / len(true_answer_indent))
    data['partial_scores'][answer_name] = {'score': round(final_score, 2), 'feedback': feedback, 'weight': answer_weight}


def test(element_html, data):
    element = lxml.html.fragment_fromstring(element_html)
    answer_name = pl.get_string_attrib(element, 'answers-name')
    answer_name_field = answer_name + '-input'

    # incorrect and correct answer test cases
    # this creates the EXPECTED SUBMISSION field for test cases
    if data['test_type'] == 'correct':
        true_answer = data['correct_answers'][answer_name]['correct_answers']
        true_answer_indent = data['correct_answers'][answer_name]['correct_answers_indent']

        data['raw_submitted_answers'][answer_name_field] = {'answers': true_answer, 'answer_indent': true_answer_indent}
        data['partial_scores'][answer_name] = {'score': 1, 'feedback': ''}
    elif data['test_type'] == 'incorrect':
        temp = data['correct_answers'][answer_name]['correct_answers'].copy()  # temp array to hold the correct answers
        incorrect_answers = []
        for html_tags in element:
            if html_tags.tag == 'pl-answer':
                incorrect_answers.append(html_tags.text)
        incorrect_answers = list(filter(lambda x: x not in temp, incorrect_answers))

        incorrect_answers_indent = ['0'] * len(incorrect_answers)
        data['raw_submitted_answers'][answer_name_field] = {'answers': incorrect_answers, 'answer_indent': incorrect_answers_indent}
        data['partial_scores'][answer_name] = {'score': 0, 'feedback': ''}

    elif data['test_type'] == 'invalid':
        data['raw_submitted_answers'][answer_name] = 'bad input'
        data['format_errors'][answer_name] = 'format error message'
    else:
        raise Exception('invalid result: %s' % data['test_type'])