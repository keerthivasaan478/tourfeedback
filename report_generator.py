import io
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import base64
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import PageBreak, ListItem, ListFlowable
from reportlab.lib.units import inch

def create_pie_chart(data, title):
    """
    Create a pie chart visualization.
    
    Args:
        data (dict): Dictionary of label-value pairs
        title (str): Chart title
        
    Returns:
        bytes: PNG image data as bytes
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(6, 4))
    
    # Create the pie chart
    labels = list(data.keys())
    values = list(data.values())
    
    # Define colors based on sentiment or category
    if 'positive' in labels:
        # Sentiment-specific colors
        colors_map = {
            'positive': '#4CAF50',  # Green
            'neutral': '#FFC107',   # Amber
            'negative': '#F44336'   # Red
        }
        colors_list = [colors_map.get(label, '#2196F3') for label in labels]
    else:
        # Use a colorful palette for categories
        colors_list = plt.cm.tab10(range(len(labels)))
    
    # Create the pie chart
    wedges, texts, autotexts = ax.pie(
        values, 
        labels=None,  # We'll add a legend instead
        autopct='%1.1f%%',
        startangle=90,
        colors=colors_list
    )
    
    # Customize the appearance
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(9)
    
    # Add a legend
    ax.legend(
        wedges, 
        labels,
        title="Legend",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )
    
    # Add title
    ax.set_title(title)
    
    # Ensure the pie is drawn as a circle
    ax.axis('equal')
    
    # Save the chart to a BytesIO object
    img_data = io.BytesIO()
    plt.tight_layout()
    fig.savefig(img_data, format='png', bbox_inches='tight')
    plt.close(fig)
    
    img_data.seek(0)
    return img_data.getvalue()

def create_bar_chart(data, title, xlabel="Categories", ylabel="Count"):
    """
    Create a bar chart visualization.
    
    Args:
        data (dict): Dictionary of label-value pairs
        title (str): Chart title
        xlabel (str): X-axis label
        ylabel (str): Y-axis label
        
    Returns:
        bytes: PNG image data as bytes
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Create the bar chart
    labels = list(data.keys())
    values = list(data.values())
    
    # Format category labels to be more readable
    formatted_labels = [label.replace('_', ' ').title() for label in labels]
    
    # Define colors based on sentiment or category
    if 'positive' in labels:
        # Sentiment-specific colors
        colors_map = {
            'positive': '#4CAF50',  # Green
            'neutral': '#FFC107',   # Amber
            'negative': '#F44336'   # Red
        }
        colors_list = [colors_map.get(label, '#2196F3') for label in labels]
    else:
        # Use a colorful palette for categories
        colors_list = plt.cm.tab10(range(len(labels)))
    
    # Create the bar chart
    bars = ax.bar(formatted_labels, values, color=colors_list)
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height + 0.1,
            f'{height:.0f}',
            ha='center', 
            va='bottom',
            fontsize=9
        )
    
    # Add labels and title
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    
    # Save the chart to a BytesIO object
    img_data = io.BytesIO()
    plt.tight_layout()
    fig.savefig(img_data, format='png', bbox_inches='tight')
    plt.close(fig)
    
    img_data.seek(0)
    return img_data.getvalue()

def generate_pdf_report(results):
    """
    Generate a PDF report from the feedback analysis results.
    
    Args:
        results (dict): Dictionary containing analysis results
        
    Returns:
        bytes: PDF report as bytes
    """
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading1_style = styles["Heading1"]
    heading2_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    # Create a list to hold the flowables
    elements = []
    
    # Add title
    elements.append(Paragraph("Tour Feedback Analysis Report", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add date
    date_str = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on: {date_str}", normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add executive summary
    elements.append(Paragraph("Executive Summary", heading1_style))
    
    # Calculate some summary statistics
    total_feedback = sum(results['sentiment_distribution'].values())
    positive_pct = (results['sentiment_distribution'].get('positive', 0) / total_feedback * 100) if total_feedback > 0 else 0
    negative_pct = (results['sentiment_distribution'].get('negative', 0) / total_feedback * 100) if total_feedback > 0 else 0
    top_category = max(results['category_distribution'].items(), key=lambda x: x[1])[0] if results['category_distribution'] else "None"
    
    summary_text = f"""
    This report analyzes {total_feedback} customer feedback entries. 
    Overall, {positive_pct:.1f}% of the feedback is positive and {negative_pct:.1f}% is negative. 
    The most discussed category is '{top_category.replace('_', ' ').title()}', 
    accounting for {results['category_distribution'].get(top_category, 0)} entries.
    """
    
    elements.append(Paragraph(summary_text, normal_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add sentiment analysis section
    elements.append(Paragraph("Sentiment Analysis", heading1_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Create sentiment distribution visualization
    if results['sentiment_distribution']:
        # Create both chart types
        pie_chart_data = create_pie_chart(
            results['sentiment_distribution'],
            "Sentiment Distribution"
        )
        bar_chart_data = create_bar_chart(
            results['sentiment_distribution'],
            "Sentiment Distribution",
            "Sentiment",
            "Count"
        )
        
        # Add the pie chart to the PDF
        img = Image(io.BytesIO(pie_chart_data), width=4*inch, height=3*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.1*inch))
        
        # Add sentiment statistics
        sentiment_data = [
            ["Sentiment", "Count", "Percentage"],
            ["Positive", results['sentiment_distribution'].get('positive', 0), f"{positive_pct:.1f}%"],
            ["Neutral", results['sentiment_distribution'].get('neutral', 0), f"{(results['sentiment_distribution'].get('neutral', 0) / total_feedback * 100):.1f}%"],
            ["Negative", results['sentiment_distribution'].get('negative', 0), f"{negative_pct:.1f}%"],
            ["Total", total_feedback, "100.0%"]
        ]
        
        sentiment_table = Table(sentiment_data, colWidths=[1.5*inch, 1*inch, 1*inch])
        sentiment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(sentiment_table)
    else:
        elements.append(Paragraph("No sentiment data available.", normal_style))
    
    elements.append(Spacer(1, 0.25*inch))
    
    # Add feedback categories section
    elements.append(Paragraph("Feedback Categories", heading1_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Create category distribution visualization
    if results['category_distribution']:
        bar_chart_data = create_bar_chart(
            results['category_distribution'],
            "Feedback by Category",
            "Category",
            "Count"
        )
        
        # Add the bar chart to the PDF
        img = Image(io.BytesIO(bar_chart_data), width=6*inch, height=3*inch)
        elements.append(img)
        elements.append(Spacer(1, 0.1*inch))
        
        # Add category statistics
        category_data = [["Category", "Count", "Percentage"]]
        for category, count in sorted(results['category_distribution'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_feedback * 100) if total_feedback > 0 else 0
            category_data.append([
                category.replace('_', ' ').title(), 
                count,
                f"{percentage:.1f}%"
            ])
        
        category_table = Table(category_data, colWidths=[2*inch, 1*inch, 1*inch])
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(category_table)
    else:
        elements.append(Paragraph("No category data available.", normal_style))
    
    elements.append(Spacer(1, 0.25*inch))
    
    # Add a page break
    elements.append(PageBreak())
    
    # Add category summaries section
    elements.append(Paragraph("Category Summaries", heading1_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if results['category_summaries']:
        for category, summary in sorted(results['category_summaries'].items()):
            # Skip empty summaries
            if not summary:
                continue
                
            category_title = category.replace('_', ' ').title()
            elements.append(Paragraph(category_title, heading2_style))
            elements.append(Paragraph(summary, normal_style))
            elements.append(Spacer(1, 0.15*inch))
    else:
        elements.append(Paragraph("No category summaries available.", normal_style))
    
    elements.append(Spacer(1, 0.25*inch))
    
    # Add a page break
    elements.append(PageBreak())
    
    # Add improvement suggestions section
    elements.append(Paragraph("Improvement Suggestions", heading1_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if results['improvement_suggestions']:
        for category, suggestions in sorted(results['improvement_suggestions'].items()):
            # Skip empty suggestions
            if not suggestions:
                continue
                
            category_title = category.replace('_', ' ').title()
            elements.append(Paragraph(category_title, heading2_style))
            
            # Create a list of suggestions
            suggestion_items = []
            for suggestion in suggestions:
                title = suggestion.get('title', 'Suggestion')
                explanation = suggestion.get('explanation', '')
                suggestion_text = f"<b>{title}</b>: {explanation}"
                suggestion_items.append(ListItem(Paragraph(suggestion_text, normal_style)))
            
            suggestion_list = ListFlowable(
                suggestion_items,
                bulletType='bullet',
                leftIndent=20,
                bulletFontSize=8,
                bulletOffsetY=2
            )
            
            elements.append(suggestion_list)
            elements.append(Spacer(1, 0.15*inch))
    else:
        elements.append(Paragraph("No improvement suggestions available.", normal_style))
    
    # Add a conclusion
    elements.append(Spacer(1, 0.25*inch))
    elements.append(Paragraph("Conclusion", heading1_style))
    elements.append(Spacer(1, 0.1*inch))
    
    conclusion_text = f"""
    This report provides an analysis of {total_feedback} customer feedback entries. 
    The insights and suggestions presented should be considered as part of a 
    comprehensive service improvement strategy. Regular analysis of customer feedback 
    is recommended to track progress and identify emerging trends.
    """
    
    elements.append(Paragraph(conclusion_text, normal_style))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the PDF from the buffer
    buffer.seek(0)
    return buffer.getvalue()
