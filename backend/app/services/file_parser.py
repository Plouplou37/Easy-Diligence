import json
import random
import time
from typing import Dict, List, Tuple, Union
import pandas as pd
import openpyxl
from io import BytesIO


class FileParsingError(Exception):
    """Custom exception for file parsing errors"""
    pass


class DDTypeFileParser:
    """Service for parsing DD Type structure files (Excel, CSV, JSON)"""

    @staticmethod
    def generate_section_code(title: str) -> str:
        """
        Generate section code following existing pattern:
        First 6 chars of title + 6-digit timestamp + 2-digit random
        """
        title_prefix = title.upper().replace(' ', '').replace('_', '')[:6]
        timestamp = str(int(time.time()))[-6:]
        random_suffix = str(random.randint(10, 99))
        return f"{title_prefix}_{timestamp}{random_suffix}"

    @staticmethod
    def generate_question_code(question_text: str, section_code: str) -> str:
        """
        Generate question code following pattern similar to section:
        First 6 chars of question + section timestamp + 2-digit random
        """
        # Extract first few words from question text
        question_prefix = ''.join(question_text.split()[:2]).upper().replace(' ', '').replace('_', '')[:6]
        # Use section's timestamp part for consistency
        section_timestamp = section_code.split('_')[1][:6] if '_' in section_code else str(int(time.time()))[-6:]
        random_suffix = str(random.randint(10, 99))
        return f"{question_prefix}_{section_timestamp}{random_suffix}"

    @staticmethod
    def generate_question_code_from_reference(reference: str, section_code: str) -> str:
        """Question code built from the reviewer's reference ("A.01").

        generate_question_code takes the first two words of the text, which is
        how the reference questionnaires' codes came to read "A.01-_<digits>": the text opened with
        "A.01 - ". Once the reference moved out of the text into its own field,
        the text would yield "WHATIS_<digits>" instead, and the reference would
        silently drop out of the code as well. The shape is kept on purpose:
        update_questionnaire.py, the PDF export and the frontend badge all read
        the reference back from it.
        """
        section_timestamp = section_code.split('_')[1][:6] if '_' in section_code else str(int(time.time()))[-6:]
        random_suffix = str(random.randint(10, 99))
        return f"{reference.strip().upper()[:20]}-_{section_timestamp}{random_suffix}"

    def parse_excel(self, file_content: bytes) -> List[Dict]:
        """
        Parse Excel file with format:
        Column A: Section (only on first row of each section)
        Column B: Question
        """
        try:
            workbook = openpyxl.load_workbook(BytesIO(file_content))
            worksheet = workbook.active

            sections = []
            current_section = None
            section_order = 0
            question_order = 0

            for row_num, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
                section_name = row[0] if len(row) > 0 and row[0] else None
                question_text = row[1] if len(row) > 1 and row[1] else None

                # Skip empty rows
                if not section_name and not question_text:
                    continue

                # New section detected
                if section_name:
                    if current_section:
                        sections.append(current_section)

                    section_code = self.generate_section_code(section_name)
                    current_section = {
                        'title': str(section_name).strip(),
                        'section_code': section_code,
                        'description': None,
                        'order_index': section_order,
                        'questions': []
                    }
                    section_order += 1
                    question_order = 0

                # Add question to current section
                if question_text and current_section:
                    question_code = self.generate_question_code(str(question_text), current_section['section_code'])
                    current_section['questions'].append({
                        'question_text': str(question_text).strip(),
                        'question_code': question_code,
                        'order_index': question_order
                    })
                    question_order += 1
                elif question_text and not current_section:
                    raise FileParsingError(f"Question found without section at row {row_num}")

            # Add last section
            if current_section:
                sections.append(current_section)

            if not sections:
                raise FileParsingError("No valid sections found in Excel file")

            return sections

        except Exception as e:
            if isinstance(e, FileParsingError):
                raise e
            raise FileParsingError(f"Error parsing Excel file: {str(e)}")

    def parse_csv(self, file_content: bytes) -> List[Dict]:
        """
        Parse CSV file with format:
        Column 1: Section (only on first row of each section)
        Column 2: Question
        """
        try:
            # Try different encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']:
                try:
                    content = file_content.decode(encoding)
                    df = pd.read_csv(BytesIO(content.encode('utf-8')))
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            else:
                raise FileParsingError("Unable to parse CSV file with any supported encoding")

            if df.empty or len(df.columns) < 2:
                raise FileParsingError("CSV must have at least 2 columns (Section, Question)")

            sections = []
            current_section = None
            section_order = 0
            question_order = 0

            for index, row in df.iterrows():
                section_name = row.iloc[0] if pd.notna(row.iloc[0]) and str(row.iloc[0]).strip() else None
                question_text = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) and str(row.iloc[1]).strip() else None

                # Skip empty rows
                if not section_name and not question_text:
                    continue

                # New section detected
                if section_name:
                    if current_section:
                        sections.append(current_section)

                    section_code = self.generate_section_code(str(section_name))
                    current_section = {
                        'title': str(section_name).strip(),
                        'section_code': section_code,
                        'description': None,
                        'order_index': section_order,
                        'questions': []
                    }
                    section_order += 1
                    question_order = 0

                # Add question to current section
                if question_text and current_section:
                    question_code = self.generate_question_code(str(question_text), current_section['section_code'])
                    current_section['questions'].append({
                        'question_text': str(question_text).strip(),
                        'question_code': question_code,
                        'order_index': question_order
                    })
                    question_order += 1
                elif question_text and not current_section:
                    raise FileParsingError(f"Question found without section at row {index + 2}")

            # Add last section
            if current_section:
                sections.append(current_section)

            if not sections:
                raise FileParsingError("No valid sections found in CSV file")

            return sections

        except Exception as e:
            if isinstance(e, FileParsingError):
                raise e
            raise FileParsingError(f"Error parsing CSV file: {str(e)}")

    def parse_json(self, file_content: bytes) -> List[Dict]:
        """
        Parse JSON file with format:
        [
            {
                "section": "Section Name",
                "questions": ["Question 1", "Question 2", ...]
            }
        ]
        """
        try:
            content = file_content.decode('utf-8')
            data = json.loads(content)

            if not isinstance(data, list):
                raise FileParsingError("JSON must be an array of section objects")

            sections = []

            for section_order, section_data in enumerate(data):
                if not isinstance(section_data, dict):
                    raise FileParsingError(f"Section {section_order + 1} must be an object")

                section_name = section_data.get('section')
                questions = section_data.get('questions', [])

                if not section_name:
                    raise FileParsingError(f"Section {section_order + 1} missing 'section' field")

                if not isinstance(questions, list):
                    raise FileParsingError(f"Questions for section '{section_name}' must be an array")

                section_code = self.generate_section_code(str(section_name))
                section = {
                    'title': str(section_name).strip(),
                    'section_code': section_code,
                    'description': section_data.get('description'),
                    'order_index': section_order,
                    'questions': []
                }

                for question_order, entry in enumerate(questions):
                    # A question is either a bare string (the original format) or
                    # an object carrying its own fields. The object form exists so
                    # a questionnaire can hold what used to be folded into the text:
                    # the "where to look" sources (context_prompt) and the reviewer's
                    # numbering (ref). With strings only, re-importing a file would
                    # push them back in.
                    if isinstance(entry, dict):
                        question_text = entry.get('text') or entry.get('question_text')
                        context_prompt = (entry.get('context_prompt') or '').strip() or None
                        reference = (entry.get('ref') or '').strip() or None
                    else:
                        question_text = entry
                        context_prompt = None
                        reference = None

                    if not question_text or not str(question_text).strip():
                        continue

                    if reference:
                        question_code = self.generate_question_code_from_reference(reference, section_code)
                    else:
                        question_code = self.generate_question_code(str(question_text), section_code)
                    section['questions'].append({
                        'question_text': str(question_text).strip(),
                        'question_code': question_code,
                        'order_index': question_order,
                        'context_prompt': context_prompt
                    })

                if section['questions']:  # Only add sections with questions
                    sections.append(section)

            if not sections:
                raise FileParsingError("No valid sections with questions found in JSON file")

            return sections

        except json.JSONDecodeError as e:
            raise FileParsingError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            if isinstance(e, FileParsingError):
                raise e
            raise FileParsingError(f"Error parsing JSON file: {str(e)}")

    def parse_file(self, file_content: bytes, filename: str) -> List[Dict]:
        """
        Parse file based on extension and return structured sections data

        Returns:
            List of sections with questions in the format:
            [
                {
                    'title': 'Section Name',
                    'section_code': 'SECTIO_123456789',
                    'description': None or str,
                    'order_index': int,
                    'questions': [
                        {
                            'question_text': 'Question text',
                            'question_code': 'QUESTI_123456789',
                            'order_index': int
                        }
                    ]
                }
            ]
        """
        filename_lower = filename.lower()

        if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
            return self.parse_excel(file_content)
        elif filename_lower.endswith('.csv'):
            return self.parse_csv(file_content)
        elif filename_lower.endswith('.json'):
            return self.parse_json(file_content)
        else:
            raise FileParsingError(f"Unsupported file format. Supported formats: .xlsx, .xls, .csv, .json")

    def validate_parsed_data(self, sections: List[Dict]) -> Tuple[bool, List[str]]:
        """
        Validate parsed sections data

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        if not sections:
            errors.append("No sections found")
            return False, errors

        section_codes = []
        question_codes = []

        for i, section in enumerate(sections):
            # Validate section structure
            required_fields = ['title', 'section_code', 'order_index', 'questions']
            for field in required_fields:
                if field not in section:
                    errors.append(f"Section {i + 1}: Missing required field '{field}'")

            # Check for duplicate section codes
            if section.get('section_code') in section_codes:
                errors.append(f"Section {i + 1}: Duplicate section code '{section.get('section_code')}'")
            else:
                section_codes.append(section.get('section_code'))

            # Validate questions
            if not section.get('questions'):
                errors.append(f"Section '{section.get('title', i + 1)}': No questions found")
            else:
                for j, question in enumerate(section['questions']):
                    # Validate question structure
                    required_q_fields = ['question_text', 'question_code', 'order_index']
                    for field in required_q_fields:
                        if field not in question:
                            errors.append(f"Section '{section.get('title')}', Question {j + 1}: Missing required field '{field}'")

                    # Check for duplicate question codes
                    if question.get('question_code') in question_codes:
                        errors.append(f"Section '{section.get('title')}', Question {j + 1}: Duplicate question code '{question.get('question_code')}'")
                    else:
                        question_codes.append(question.get('question_code'))

        return len(errors) == 0, errors