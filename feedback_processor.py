import pandas as pd
import os
import google.generativeai as genai
from collections import Counter
import json
import time
import re

# Setup Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    raise ValueError("Google API Key not found. Please set the GOOGLE_API_KEY environment variable.")

def get_gemini_model():
    """Get the Gemini Pro model for text processing."""
    try:
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        raise Exception(f"Error initializing Gemini model: {str(e)}")

def process_single_feedback(feedback_text, model):
    """
    Process a single feedback entry with Gemini API to extract sentiment and category.
    
    Args:
        feedback_text (str): The text of the feedback
        model: The Gemini model instance
        
    Returns:
        dict: Dictionary containing sentiment, category, and other extracted information
    """
    prompt = f"""
    Analyze the following tour operator customer feedback:
    
    "{feedback_text}"
    
    Please provide a JSON object with the following fields:
    1. "sentiment": Classify the sentiment as "positive", "negative", or "neutral"
    2. "category": Assign the feedback to ONE of these categories: "accommodation", "transportation", "food_dining", "activities_guides", "booking_process", "value_for_money", or "other"
    3. "key_points": Extract up to 3 key points from the feedback (list of strings)
    
    Return ONLY the JSON object, nothing else.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Extract the JSON from the response
        response_text = response.text
        
        # Find JSON object in the response (handling potential code block formatting)
        json_match = re.search(r'```json\n(.*?)\n```|```(.*?)```|({.*})', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1) or json_match.group(2) or json_match.group(3)
            result = json.loads(json_str)
        else:
            # If not in code blocks, try to parse the entire response
            result = json.loads(response_text)
        
        return result
    except Exception as e:
        # In case of error, return a default result
        print(f"Error processing feedback: {str(e)}")
        return {
            "sentiment": "neutral",
            "category": "other",
            "key_points": ["Could not extract key points"]
        }

def generate_category_summaries(category_data, model):
    """
    Generate summaries for each feedback category using Gemini API.
    
    Args:
        category_data (dict): Dictionary mapping categories to lists of feedback
        model: The Gemini model instance
        
    Returns:
        dict: Dictionary of category summaries
    """
    summaries = {}
    
    for category, feedbacks in category_data.items():
        # Skip if there are no feedbacks for this category
        if not feedbacks:
            continue
            
        # Limit the number of feedbacks to prevent prompt size issues
        sample_size = min(20, len(feedbacks))
        sample_feedbacks = feedbacks[:sample_size]
        
        # Create prompt for summarization
        prompt = f"""
        Analyze the following {sample_size} customer feedback entries for a tour operator 
        in the category "{category.replace('_', ' ')}":
        
        {json.dumps(sample_feedbacks)}
        
        Based on these feedbacks, provide a concise summary (maximum 150 words) that:
        1. Identifies common themes or patterns
        2. Highlights major strengths and areas of concern
        3. Quantifies the general sentiment (mostly positive, mixed, mostly negative)
        
        Return ONLY the summary text, nothing else.
        """
        
        try:
            response = model.generate_content(prompt)
            summaries[category] = response.text.strip()
        except Exception as e:
            summaries[category] = f"Could not generate summary for {category}: {str(e)}"
    
    return summaries

def generate_improvement_suggestions(category_data, model):
    """
    Generate improvement suggestions for each feedback category using Gemini API.
    
    Args:
        category_data (dict): Dictionary mapping categories to lists of feedback
        model: The Gemini model instance
        
    Returns:
        dict: Dictionary of improvement suggestions by category
    """
    suggestions = {}
    
    for category, feedbacks in category_data.items():
        # Skip if there are no feedbacks for this category
        if not feedbacks:
            continue
            
        # Limit the number of feedbacks to prevent prompt size issues
        sample_size = min(20, len(feedbacks))
        sample_feedbacks = feedbacks[:sample_size]
        
        # Create prompt for generating improvement suggestions
        prompt = f"""
        You are an expert tourism consultant helping a tour operator improve their services.
        
        Review these {sample_size} customer feedback entries in the category "{category.replace('_', ' ')}":
        
        {json.dumps(sample_feedbacks)}
        
        Based on these feedbacks, provide 3-5 specific, actionable improvement suggestions that:
        1. Address common pain points or concerns
        2. Are practical and implementable
        3. Would significantly improve customer satisfaction
        
        For each suggestion, provide:
        - A brief title (1-5 words)
        - A concise explanation (1-2 sentences)
        
        Format as a JSON array of objects with "title" and "explanation" properties.
        Return ONLY the JSON array, nothing else.
        """
        
        try:
            response = model.generate_content(prompt)
            
            # Extract the JSON array from the response
            response_text = response.text
            
            # Find JSON object in the response (handling potential code block formatting)
            json_match = re.search(r'```json\n(.*?)\n```|```(.*?)```|(\[.*\])', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2) or json_match.group(3)
                result = json.loads(json_str)
            else:
                # If not in code blocks, try to parse the entire response
                result = json.loads(response_text)
                
            suggestions[category] = result
        except Exception as e:
            # In case of error, provide a default suggestion
            suggestions[category] = [
                {
                    "title": "Improve based on feedback",
                    "explanation": f"Review customer feedback for {category.replace('_', ' ')} to identify specific improvement areas."
                }
            ]
    
    return suggestions

def process_feedback(df, include_sentiment=True, include_categorization=True, include_summaries=True, include_suggestions=True, feedback_format="text"):
    """
    Process the feedback data using the Gemini API.
    
    Args:
        df (pandas.DataFrame): DataFrame containing the feedback data
        include_sentiment (bool): Whether to include sentiment analysis
        include_categorization (bool): Whether to include feedback categorization
        include_summaries (bool): Whether to include category summaries
        include_suggestions (bool): Whether to include improvement suggestions
        feedback_format (str): Format of the feedback data ('text', 'json', 'csv')
        
    Returns:
        dict: Dictionary containing analysis results
    """
    results = {
        'sentiment_distribution': Counter(),
        'category_distribution': Counter(),
        'category_summaries': {},
        'improvement_suggestions': {},
        'processed_data': pd.DataFrame()
    }
    
    # Initialize Gemini model
    model = get_gemini_model()
    
    # Determine the column containing feedback text
    feedback_column = None
    
    # Try to identify the feedback column based on column names
    potential_columns = [
        'feedback', 'review', 'comment', 'text', 'description', 
        'response', 'comments', 'reviews', 'message', 'content'
    ]
    
    for col in df.columns:
        if col.lower() in potential_columns:
            feedback_column = col
            break
    
    # If no specific feedback column was identified, use the first string column
    if feedback_column is None:
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns are typically 'object' dtype
                # Check if the column contains text-like data (not just identifiers)
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                if isinstance(sample, str) and len(sample) > 10:  # Simple heuristic for text
                    feedback_column = col
                    break
    
    # If we still couldn't find a suitable column, use the first column
    if feedback_column is None and len(df.columns) > 0:
        feedback_column = df.columns[0]
    
    if feedback_column is None:
        raise ValueError("Could not identify a suitable feedback column in the data")
    
    # Create a new DataFrame to store processed data
    processed_df = df.copy()
    processed_df['sentiment'] = 'neutral'
    processed_df['category'] = 'other'
    processed_df['key_points'] = [[] for _ in range(len(df))]
    
    # Create a dictionary to organize feedback by category
    category_data = {
        'accommodation': [],
        'transportation': [],
        'food_dining': [],
        'activities_guides': [],
        'booking_process': [],
        'value_for_money': [],
        'other': []
    }
    
    # Process each feedback entry
    for idx, row in df.iterrows():
        feedback_text = str(row[feedback_column])
        
        # Skip empty feedback
        if not feedback_text or feedback_text.isspace():
            continue
            
        # Process with Gemini API
        analysis_result = process_single_feedback(feedback_text, model)
        
        # Update the DataFrame with analysis results
        processed_df.at[idx, 'sentiment'] = analysis_result.get('sentiment', 'neutral')
        processed_df.at[idx, 'category'] = analysis_result.get('category', 'other')
        processed_df.at[idx, 'key_points'] = analysis_result.get('key_points', [])
        
        # Update counters
        results['sentiment_distribution'][analysis_result.get('sentiment', 'neutral')] += 1
        results['category_distribution'][analysis_result.get('category', 'other')] += 1
        
        # Add to category data for summaries and suggestions
        category = analysis_result.get('category', 'other')
        category_data[category].append(feedback_text)
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.1)
    
    # Generate category summaries if requested
    if include_summaries:
        results['category_summaries'] = generate_category_summaries(category_data, model)
    
    # Generate improvement suggestions if requested
    if include_suggestions:
        results['improvement_suggestions'] = generate_improvement_suggestions(category_data, model)
    
    # Update the results with processed data
    results['processed_data'] = processed_df
    
    return results
