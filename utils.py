import pandas as pd
import streamlit as st
import io
import json
import csv

def parse_file(uploaded_file, file_extension):
    """
    Parse the uploaded file based on its extension.
    
    Args:
        uploaded_file: The uploaded file object
        file_extension: The file extension (txt, csv, json)
        
    Returns:
        tuple: (DataFrame containing the parsed data, format description)
    """
    try:
        file_extension = file_extension.lower()
        
        if file_extension == 'csv':
            return parse_csv(uploaded_file)
        elif file_extension == 'json':
            return parse_json(uploaded_file)
        elif file_extension == 'txt':
            return parse_txt(uploaded_file)
        else:
            st.warning(f"Unsupported file extension: {file_extension}. Attempting to parse as plain text.")
            # Try to parse as text by default
            return parse_txt(uploaded_file)
            
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        # Create a fallback DataFrame
        df = pd.DataFrame({'feedback': ["Error parsing file - please check format and try again"]})
        return df, "parsing error"

def parse_csv(uploaded_file):
    """Parse a CSV file into a DataFrame."""
    try:
        # Try to detect the delimiter
        sample = uploaded_file.read(1024).decode('utf-8', errors='replace')
        uploaded_file.seek(0)  # Reset the file pointer
        
        # Try to detect delimiter using csv.Sniffer
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            delimiter = dialect.delimiter
        except:
            # Default to comma if sniffer fails
            delimiter = ','
            st.info("Could not detect CSV delimiter, using comma as default.")
        
        # Try reading with pandas, handling various issues
        try:
            df = pd.read_csv(uploaded_file, delimiter=delimiter, error_bad_lines=False, warn_bad_lines=True)
        except:
            # For older pandas versions without error_bad_lines
            try:
                df = pd.read_csv(uploaded_file, delimiter=delimiter, on_bad_lines='skip')
            except:
                # Last resort: try with default settings
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file)
        
        # Check if we got any data
        if df.empty:
            st.warning("The CSV file appears to be empty or could not be properly parsed.")
            df = pd.DataFrame({'feedback': ["CSV parsing resulted in no data - please check file format"]})
        
        return df, "csv"
    except Exception as e:
        st.error(f"Error parsing CSV file: {str(e)}")
        # Return a minimal valid DataFrame instead of raising an exception
        df = pd.DataFrame({'feedback': ["Error in CSV parsing - this is a placeholder entry"]})
        return df, "csv with parsing error"

def parse_json(uploaded_file):
    """Parse a JSON file into a DataFrame."""
    try:
        # Read file content as string first
        content_str = uploaded_file.read().decode('utf-8', errors='replace')
        uploaded_file.seek(0)  # Reset file pointer
        
        # Try to load JSON
        try:
            content = json.loads(content_str)
        except json.JSONDecodeError as e:
            # Try to fix common JSON issues and retry
            st.warning(f"JSON parsing error: {str(e)}. Attempting to fix...")
            
            # Try to handle single quotes instead of double quotes
            try:
                import ast
                content = ast.literal_eval(content_str)
            except:
                # If that fails, try a more aggressive approach with line-by-line parsing
                try:
                    lines = content_str.strip().split('\n')
                    # Simply treat each line as a separate feedback entry
                    df = pd.DataFrame({'feedback': lines})
                    return df, "json-like text"
                except:
                    st.error("Could not parse the JSON file after multiple attempts.")
                    df = pd.DataFrame({'feedback': ["Invalid JSON format - please check file structure"]})
                    return df, "invalid json"
        
        # Handle different JSON structures
        if isinstance(content, list):
            # JSON is a list of objects/dictionaries
            if all(isinstance(item, str) for item in content):
                # List of strings - treat each string as a feedback entry
                df = pd.DataFrame({'feedback': content})
            else:
                # List of objects
                df = pd.DataFrame(content)
        elif isinstance(content, dict):
            # JSON is a dictionary
            if any(isinstance(content[key], list) for key in content):
                # Dictionary with lists, find the most likely feedback list
                list_keys = [k for k in content if isinstance(content[k], list)]
                
                if list_keys:
                    # First check for common feedback-related keys
                    feedback_related_keys = ['feedback', 'reviews', 'comments', 'responses', 'data']
                    for key in feedback_related_keys:
                        if key in list_keys:
                            df = pd.DataFrame(content[key])
                            break
                    else:
                        # If no feedback-related key found, use the longest list
                        max_list_key = max(list_keys, key=lambda k: len(content[k]), default=None)
                        if max_list_key and content[max_list_key]:
                            df = pd.DataFrame(content[max_list_key])
                        else:
                            # Fallback: convert the whole dict to a single-row DataFrame
                            df = pd.DataFrame([content])
                else:
                    # No lists in the dictionary
                    df = pd.DataFrame([content])
            else:
                # Simple dictionary, convert to single-row DataFrame
                df = pd.DataFrame([content])
        else:
            # Handle primitive types (unlikely but possible)
            df = pd.DataFrame({'feedback': [str(content)]})
            
        # If dataframe is empty or has no valid columns, create a default
        if df.empty:
            st.warning("The JSON data could not be converted to a usable DataFrame.")
            df = pd.DataFrame({'feedback': ["JSON parsing resulted in no usable data - please check format"]})
            
        return df, "json"
    except Exception as e:
        st.error(f"Error parsing JSON file: {str(e)}")
        # Return a minimal valid DataFrame instead of raising an exception
        df = pd.DataFrame({'feedback': ["Error in JSON parsing - this is a placeholder entry"]})
        return df, "json with parsing error"

def parse_txt(uploaded_file):
    """Parse a text file into a DataFrame."""
    try:
        content = uploaded_file.read().decode('utf-8', errors='replace')
        
        # Split the content by lines
        lines = content.strip().split('\n')
        
        # Filter out empty lines
        lines = [line.strip() for line in lines if line.strip()]
        
        # If no valid lines found, create at least one empty entry
        if not lines:
            lines = ["No content found in file"]
            st.warning("The uploaded text file appears to be empty. Adding a placeholder entry.")
        
        # Check if the file might be a CSV
        if any(',' in line for line in lines[:10]) and len(lines) > 1:
            # If it looks like a CSV, try to parse it as such
            uploaded_file.seek(0)  # Reset the file pointer
            try:
                df = pd.read_csv(uploaded_file)
                return df, "csv-like text"
            except:
                # If CSV parsing fails, continue with text processing
                uploaded_file.seek(0)
                content = uploaded_file.read().decode('utf-8', errors='replace')
                lines = content.strip().split('\n')
                lines = [line.strip() for line in lines if line.strip()]
        
        # Create a DataFrame with one feedback per row
        df = pd.DataFrame({'feedback': lines})
        
        if 'feedback' not in df.columns or df.empty:
            df = pd.DataFrame({'feedback': ["Sample feedback entry - please replace with actual data"]})
            st.warning("Couldn't parse the text file properly. Created a sample entry for demonstration.")
        
        return df, "text"
    except Exception as e:
        st.error(f"Error parsing text file: {str(e)}")
        # Return a minimal valid DataFrame instead of raising an exception
        df = pd.DataFrame({'feedback': ["Error in file parsing - this is a placeholder entry"]})
        return df, "text with parsing error"

def display_sample_data(df, feedback_format):
    """
    Display a sample of the uploaded data.
    
    Args:
        df: DataFrame containing the parsed data
        feedback_format: Description of the data format
    """
    st.write(f"Data format: {feedback_format}")
    
    # Calculate the number of rows to display (max 10)
    num_rows = min(10, len(df))
    
    # Display the sample data
    st.dataframe(df.head(num_rows))
    
    # Display column information
    st.write("Column Information:")
    
    # Get column info
    column_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].count()
        null_percent = (1 - non_null / len(df)) * 100 if len(df) > 0 else 0
        sample_val = str(df[col].iloc[0]) if not df[col].empty else ""
        if len(sample_val) > 50:
            sample_val = sample_val[:47] + "..."
            
        column_info.append({
            "Column": col,
            "Type": dtype,
            "Non-Null Count": f"{non_null}/{len(df)}",
            "Null %": f"{null_percent:.1f}%",
            "Sample Value": sample_val
        })
    
    # Display as a table
    st.table(pd.DataFrame(column_info))
