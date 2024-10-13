import os
from flask import Flask, request, render_template
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

app = Flask(__name__)

# Load the dataset
df = pd.read_csv(os.path.join(os.getcwd(), 'UdemyCleanedTitle.csv'))

# Handle NaN values in the 'Clean_title' column
df['Clean_title'] = df['Clean_title'].fillna('')  # Replace NaN with empty string

# Create a CountVectorizer object
count_vect = CountVectorizer(stop_words='english')
cv_mat = count_vect.fit_transform(df['Clean_title'])

# Calculate cosine similarity
cosine_sim_mat = cosine_similarity(cv_mat)

# Create a Series with course titles as index and their respective index as values
course_indices = pd.Series(df.index, index=df['course_title']).drop_duplicates()

def recommend_courses(title, num_recommendations=10):
    """
    Recommend courses based on the given course title.

    Args:
    title (str): The title of the course to base recommendations on.
    num_recommendations (int): The number of recommendations to return.

    Returns:
    pd.DataFrame: A dataframe of recommended courses with their details.
    """
    # Get the index of the course that matches the title
    idx = course_indices[title]

    # Get the pairwise similarity scores of all courses with that course
    sim_scores = list(enumerate(cosine_sim_mat[idx]))

    # Sort the courses based on the similarity scores
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    # Get the scores of the most similar courses
    sim_scores = sim_scores[1:num_recommendations+1]

    # Get the course indices
    recommended_indices = [i[0] for i in sim_scores]

    # Return the top most similar courses
    recommended_courses = df.iloc[recommended_indices][['course_title', 'url', 'price', 'num_subscribers']]
    recommended_courses['similarity_score'] = [i[1] for i in sim_scores]

    return recommended_courses

def search_term(term, df):
    """
    Search for courses containing the given term in their title.

    Args:
    term (str): The search term.
    df (pd.DataFrame): The dataframe containing course data.

    Returns:
    pd.DataFrame: A dataframe of courses matching the search term.
    """
    result_df = df[df['course_title'].str.contains(term, case=False, na=False)]
    return result_df.sort_values(by='num_subscribers', ascending=False).head(6)

@app.route('/', methods=['GET', 'POST'])
def home():
    coursemap = {}  # Initialize coursemap as an empty dictionary
    coursename = ""
    showtitle = False
    showerror = False

    if request.method == 'POST':
        coursename = request.form['course']
        try:
            recommendations = recommend_courses(coursename, 6)
            coursemap = dict(zip(recommendations['course_title'], recommendations['url']))
            showtitle = True
        except KeyError:
            # If the exact course title is not found, perform a search
            search_results = search_term(coursename, df)
            if not search_results.empty:
                coursemap = dict(zip(search_results['course_title'], search_results['url']))
                showtitle = True
            else:
                showerror = True

    return render_template('index.html', coursemap=coursemap, coursename=coursename, showtitle=showtitle, showerror=showerror)

def parse_date(date_string):
    try:
        return pd.to_datetime(date_string, format='%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        try:
            return pd.to_datetime(date_string, format='%m/%d/%Y')
        except ValueError:
            return pd.NaT

def int64_to_int(value):
    if isinstance(value, np.int64):
        return int(value)
    return value

@app.route('/dashboard')
def dashboard():
    # Number of Subscribers Domain Wise
    valuecounts = df['subject'].value_counts().to_dict()
    valuecounts = {k: int64_to_int(v) for k, v in valuecounts.items()}

    # Number of Courses Level Wise
    levelcounts = df.groupby(['level'])['num_subscribers'].count().to_dict()
    levelcounts = {k: int64_to_int(v) for k, v in levelcounts.items()}

    # Subjects per Level
    subjectsperlevel = df.groupby(['subject', 'level']).size().to_dict()
    subjectsperlevel = {f"{k[0]}_{k[1]}": int64_to_int(v) for k, v in subjectsperlevel.items()}

    # Year-wise profit and subscribers count
    df['price'] = df['price'].astype('float')
    df['profit'] = df['price'] * df['num_subscribers']
    
    # Use the custom parse_date function
    df['published_date'] = df['published_timestamp'].apply(parse_date)
    
    # Remove rows with invalid dates
    df_valid = df.dropna(subset=['published_date'])

    df_valid['Year'] = df_valid['published_date'].dt.year
    df_valid['Month'] = df_valid['published_date'].dt.month
    df_valid['Day'] = df_valid['published_date'].dt.day
    df_valid['Month_name'] = df_valid['published_date'].dt.month_name()

    yearwiseprofitmap = df_valid.groupby(['Year'])['profit'].sum().to_dict()
    yearwiseprofitmap = {int64_to_int(k): int64_to_int(v) for k, v in yearwiseprofitmap.items()}

    subscriberscountmap = df_valid.groupby(['Year'])['num_subscribers'].sum().to_dict()
    subscriberscountmap = {int64_to_int(k): int64_to_int(v) for k, v in subscriberscountmap.items()}

    profitmonthwise = df_valid.groupby(['Month_name'])['profit'].sum().to_dict()
    profitmonthwise = {k: int64_to_int(v) for k, v in profitmonthwise.items()}

    monthwisesub = df_valid.groupby(['Month_name'])['num_subscribers'].sum().to_dict()
    monthwisesub = {k: int64_to_int(v) for k, v in monthwisesub.items()}

    return render_template('dashboard.html', 
                           valuecounts=list(valuecounts.keys()),
                           valuecounts_values=list(valuecounts.values()),
                           levelcounts=list(levelcounts.keys()),
                           levelcounts_values=list(levelcounts.values()),
                           subjectsperlevel=list(subjectsperlevel.keys()),
                           subjectsperlevel_values=list(subjectsperlevel.values()),
                           yearwiseprofitmap=list(yearwiseprofitmap.keys()),
                           yearwiseprofitmap_values=list(yearwiseprofitmap.values()),
                           subscriberscountmap=list(subscriberscountmap.keys()),
                           subscriberscountmap_values=list(subscriberscountmap.values()),
                           profitmonthwise=list(profitmonthwise.keys()),
                           profitmonthwise_values=list(profitmonthwise.values()),
                           monthwisesub=list(monthwisesub.keys()),
                           monthwisesub_values=list(monthwisesub.values()))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)