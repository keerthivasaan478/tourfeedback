import streamlit as st
import pandas as pd
import os
import tempfile
import io
from datetime import datetime

from feedback_processor import process_feedback
from report_generator import generate_pdf_report
from utils import parse_file, display_sample_data

# Set page configuration
st.set_page_config(
    page_title="Tour Feedback Analyzer",
    page_icon="📊",
    layout="wide"
)

# Title and description
st.title("🏝️ AI-Based Tour Feedback Analyzer")
st.markdown("""
This tool helps tour operators analyze customer feedback and generate actionable improvement suggestions.
Upload your feedback data (reviews, surveys, emails) and get a comprehensive analysis report.
""")

# File upload section
st.header("Upload Feedback Data")
uploaded_file = st.file_uploader(
    "Upload your feedback data (TXT, CSV, JSON)", 
    type=["txt", "csv", "json"],
    help="Upload customer feedback from reviews, surveys, or emails."
)

# Sample data display and processing options
if uploaded_file is not None:
    # Get file extension
    file_extension = uploaded_file.name.split('.')[-1].lower()
    
    try:
        # Parse the uploaded file
        df, feedback_format = parse_file(uploaded_file, file_extension)
        
        if df is not None:
            # Check if we have valid data
            if df.empty:
                st.warning("The file was parsed, but no data was found. Using a sample entry for demonstration.")
                df = pd.DataFrame({'feedback': ["Sample feedback entry for demonstration - please upload valid data"]})
                feedback_format = "empty file"
                    
            st.success(f"Successfully loaded {len(df)} feedback entries")
            
            # Display sample data
            with st.expander("Preview uploaded data", expanded=True):
                display_sample_data(df, feedback_format)
            
            # Processing options
            st.header("Analysis Options")
            
            col1, col2 = st.columns(2)
            with col1:
                include_sentiment = st.checkbox("Perform Sentiment Analysis", value=True)
                include_categorization = st.checkbox("Categorize Feedback", value=True)
            
            with col2:
                include_summaries = st.checkbox("Generate Category Summaries", value=True)
                include_suggestions = st.checkbox("Generate Improvement Suggestions", value=True)
            
            # Debug info for column detection
            with st.expander("Feedback Column Detection", expanded=False):
                st.info("The application will automatically detect which column contains your feedback text.")
                st.markdown("""
                **Priority for detection:**
                1. Columns named: feedback, review, comment, text, description, etc.
                2. First text column with sufficient content
                3. First column as fallback
                
                If detection is incorrect, consider renaming your columns before uploading.
                """)
            
            # Process button
            if st.button("Analyze Feedback", type="primary"):
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Process the feedback using Gemini API
                status_text.text("Analyzing feedback...")
                
                try:
                    # Process in chunks to show progress
                    total_chunks = min(10, len(df))
                    chunk_size = max(1, len(df) // total_chunks)
                    
                    results = {}
                    processed_df = pd.DataFrame()
                    
                    # Cache for potential errors
                    error_messages = []
                    
                    for i in range(total_chunks):
                        start_idx = i * chunk_size
                        end_idx = min(start_idx + chunk_size, len(df))
                        chunk = df.iloc[start_idx:end_idx]
                        
                        # Update progress
                        progress = (i + 1) / total_chunks
                        progress_bar.progress(progress)
                        status_text.text(f"Processing entries {start_idx+1} to {end_idx} of {len(df)}...")
                        
                        try:
                            # Process the chunk
                            chunk_results = process_feedback(
                                chunk, 
                                include_sentiment=include_sentiment,
                                include_categorization=include_categorization,
                                include_summaries=include_summaries,
                                include_suggestions=include_suggestions,
                                feedback_format=feedback_format
                            )
                            
                            # Accumulate results
                            if i == 0:
                                results = chunk_results
                                processed_df = chunk_results['processed_data']
                            else:
                                # Update counters
                                for key in ['sentiment_distribution', 'category_distribution']:
                                    if key in results and key in chunk_results:
                                        for k, v in chunk_results[key].items():
                                            results[key][k] = results[key].get(k, 0) + v
                                
                                # Update dictionaries
                                for key in ['category_summaries', 'improvement_suggestions']:
                                    if key in results and key in chunk_results:
                                        results[key].update(chunk_results[key])
                                
                                # Concatenate processed data
                                if 'processed_data' in chunk_results:
                                    processed_df = pd.concat([processed_df, chunk_results['processed_data']])
                                
                        except Exception as chunk_error:
                            error_msg = f"Error processing chunk {i+1}: {str(chunk_error)}"
                            error_messages.append(error_msg)
                            st.warning(error_msg)
                            # Continue with the next chunk instead of breaking
                    
                    # Store the processed data in the results
                    if 'processed_data' not in results:
                        results['processed_data'] = processed_df
                    else:
                        results['processed_data'] = processed_df
                    
                    # Check if we have any results to display
                    if not results or (
                        'sentiment_distribution' not in results and 
                        'category_distribution' not in results and
                        'category_summaries' not in results and
                        'improvement_suggestions' not in results
                    ):
                        st.error("No analysis results were generated. Please check your data and try again.")
                        if error_messages:
                            st.error("Errors encountered during processing:")
                            for msg in error_messages:
                                st.error(msg)
                        # Skip the rest of the processing
                        pass
                    
                    # Update progress to 100%
                    progress_bar.progress(1.0)
                    status_text.text("Analysis complete!")
                    
                    # Display results summary
                    st.header("Analysis Results")
                    
                    # Show any errors that occurred during processing
                    if error_messages:
                        with st.expander("Processing Warnings", expanded=False):
                            st.warning("Some entries could not be processed:")
                            for msg in error_messages:
                                st.warning(msg)
                    
                    # Sentiment distribution
                    if include_sentiment and 'sentiment_distribution' in results and results['sentiment_distribution']:
                        st.subheader("Sentiment Distribution")
                        sentiment_counts = results['sentiment_distribution']
                        st.bar_chart(sentiment_counts)
                    
                    # Category distribution
                    if include_categorization and 'category_distribution' in results and results['category_distribution']:
                        st.subheader("Feedback Categories")
                        category_counts = results['category_distribution']
                        st.bar_chart(category_counts)
                    
                    # Generate the PDF report
                    status_text.text("Generating PDF report...")
                    report_content = generate_pdf_report(results)
                    
                    # Provide download button for the report
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"feedback_analysis_{timestamp}.pdf"
                    
                    st.download_button(
                        label="Download PDF Report",
                        data=report_content,
                        file_name=filename,
                        mime="application/pdf",
                        help="Download the complete analysis report as a PDF file"
                    )
                    
                    status_text.text("Report ready for download!")
                    
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
                    st.exception(e)
        else:
            st.error("Could not extract feedback data from the uploaded file. Please check the file format and try again.")
    
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        st.exception(e)
else:
    # Instructions when no file is uploaded
    st.info("""
    ### How to use this tool:
    1. Upload your feedback data file (TXT, CSV, or JSON format)
    2. Configure analysis options
    3. Click "Analyze Feedback" to process the data
    4. Download the generated PDF report with insights and suggestions
    
    The tool will analyze sentiment, categorize feedback, and generate improvement suggestions.
    """)

# Add footer
st.markdown("---")
st.markdown("""
<div style="text-align: center">
    <p>Powered by Google Gemini API | Tour Feedback Analyzer Tool</p>
</div>
""", unsafe_allow_html=True)
