import os
from dotenv import load_dotenv
import pickle
import requests
from langchain_text_splitters import HTMLSectionSplitter, RecursiveCharacterTextSplitter
from helpers import roman_to_int
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


def download_and_load_novel():
    filename = 'novel/768-h.htm'
    # Download
    if not os.path.exists(filename):
        url = 'https://www.gutenberg.org/files/768/768-h/768-h.htm'
        response = requests.get(url)
        response.raise_for_status()

        os.makedirs('novel', exist_ok=True)  # Create the 'novel' folder if it doesn't exist
        encoding = response.encoding or 'utf-8'
        with open(filename, 'w', encoding=encoding) as file:
            file.write(response.text)

        print('Novel file downloaded successfully.')

    else:
        print('Novel file already exists. Skipping download.')

    # Load to string
    with open(filename, 'r', encoding='utf-8') as file:
        html_string = file.read()

    # Remove the html comment <!--end chapter-->
    html_string = html_string.replace('<!--end chapter-->', '')
    html_string = html_string.replace('\n* * * * * *\n', '')
    html_string = html_string.replace('\n* * * * *\n', '')

    return html_string


def split_into_chunks(html_string):
    # Set up the HTMLSectionSplitter and split by chapters
    # The chapters are under the h2 tags
    html_splitter = HTMLSectionSplitter(
        headers_to_split_on=[('h1', 'Header 1'), ('h2', 'chapter')]
    )
    chapter_splits = html_splitter.split_text(html_string)

    # Filter the actual chapter contents
    chapter_splits = chapter_splits[3:]  # Chapters start from the 3rd split
    chapter_splits[-1].page_content = chapter_splits[-1].page_content.split(
        ' *** END OF THE PROJECT GUTENBERG EBOOK WUTHERING HEIGHTS ***')[0].strip()  # Cut off the non chapter content

    # Convert Roman numeral string to an integer (ex. 'Chapter IV' to 4)
    for split in chapter_splits:
        chapter = roman_to_int(split.metadata['chapter'].replace('CHAPTER ', ''))
        split.metadata['chapter'] = chapter

    for split in chapter_splits:
        # Clear the line breaks within sentences
        split.page_content = split.page_content.replace('\n\n', ' ')

        # Simplify the newline characters between paragraphs
        split.page_content = split.page_content.replace(' \n ', '\n')
        split.page_content = split.page_content.replace('\n\n\n', '\n\n')

        split.page_content = split.page_content.replace('Mr.\n', 'Mr. ')
        split.page_content = split.page_content.replace('Mrs.\n', 'Mrs. ')

    # Save the chapter_splits to a pickle file
    os.makedirs('splits', exist_ok=True)  # Create the 'splits' folder if it doesn't exist
    with open('splits/chapter_splits.pkl', 'wb') as file:
        pickle.dump(chapter_splits, file)

    # Further split each chapter into smaller chunks
    rct_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=['\n\n', '\n'
                    '.”', '?”', '!”',
                    '.“', '?“', '!“',
                    '.', '?', '!', ';', '-', ',', ' '
                    ],
        keep_separator='end'
    )
    paragraph_splits = rct_splitter.split_documents(chapter_splits)  # Using split_documents will keep the metadata

    # Save the chapter_splits to a pickle file
    os.makedirs('splits', exist_ok=True)  # Create the 'splits' folder if it doesn't exist
    with open('splits/paragraph_splits.pkl', 'wb') as file:
        pickle.dump(paragraph_splits, file)


def create_vectorstore():
    # Set the embedding model
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")  # TODO: one of the environment variables

    persist_directory = 'chroma_db/paragraphs'  # where to save the db

    # Load documents
    with open('splits/paragraph_splits.pkl', 'rb') as file:
        paragraph_splits = pickle.load(file)

    # Create the Chroma vectorstore
    vectorstore = Chroma(persist_directory=persist_directory, collection_name='paragraphs',
                         embedding_function=embeddings)

    # Add documents
    vectorstore.add_documents(documents=paragraph_splits)


def preprocess():
    # Load environment variables from .env file if it exists (for local execution.)
    if os.path.exists('.env'):
        load_dotenv()

    # Load the novel and split into chunks
    if not os.path.exists('splits/paragraph_splits.pkl'):
        novel_string = download_and_load_novel()
        split_into_chunks(novel_string)
        print('Chunk files created successfully.')

    else:
        print("Chunk files already exists. Skipping splitting.")

    # Create vectorstore
    if not os.path.exists('chroma_db/paragraphs'):
        create_vectorstore()
        print('Vectorstore created successfully.')
    else:
        print("Vectorstore already exists. Skipping indexing.")

