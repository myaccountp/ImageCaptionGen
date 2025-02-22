import streamlit as st
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration, ConvNextImageProcessor, ConvNextForImageClassification
from PIL import Image
import logging
from flask import Flask, request, jsonify

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load the models and processors
convnext_processor = ConvNextImageProcessor.from_pretrained("facebook/convnext-large-224")
convnext_model = ConvNextForImageClassification.from_pretrained("facebook/convnext-large-224")
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-large")

# Move models to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
convnext_model.to(device)
blip_model.to(device)

# Streamlit interface setup
st.set_page_config(page_title="Image Caption Generator", page_icon=":camera:", layout="centered")

# Style for the app
st.markdown("""
    <style>
        body {
            background-color: #f0f2f6; /* Light gray background */
        }
        .main {
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.2);
            background-color: white; /* White card background */
            max-width: 800px; /* Limit width */
            margin: auto; /* Center the card */
            overflow-y: auto; /* Enable scrolling */
            max-height: 80vh; /* Limit height */
        }
        h1 {
            color: red; /* Title color */
            font-weight: 700;
            font-size: 36px; /* Increase font size */
            text-align: center; /* Center align title */
        }
        h2 {
            font-weight: bold;
            font-size: 32px;
            color: #0033cc; /* Dark blue for caption */
            text-align: center; /* Center align caption */
        }
        .button {
            font-size: 18px;
            background-color: #f63366; /* Button background color */
            color: white; /* Button text color */
            padding: 12px 24px; /* Padding for the button */
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease; /* Smooth transition */
            display: block; /* Make button a block element */
            margin: 20px auto; /* Center align button */
        }
        .button:hover {
            background-color: #e0245e; /* Button hover color */
        }
        .file-uploader {
            margin: 20px 0; /* Add margin to file uploader */
        }
    </style>
""", unsafe_allow_html=True)

# Streamlit app interface
st.title("Image Caption Generator")
st.write("")

# Scrollable container for main content
with st.container():
    # Image upload
    uploaded_image = st.file_uploader("Choose an image file (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    # Define functions for preprocessing, feature extraction, and caption generation
    def preprocess_image(image):
        img = Image.open(image).convert("RGB")
        inputs = convnext_processor(images=img, return_tensors="pt").to(device)
        return inputs

    def extract_features(image):
        inputs = preprocess_image(image)
        with torch.no_grad():
            outputs = convnext_model(**inputs)
            features = outputs.logits
        return features

    def generate_caption(image, max_length=50, num_beams=5):
        image = Image.open(image).convert("RGB")
        blip_inputs = blip_processor(images=image, return_tensors="pt").to(device)
        with torch.no_grad():
            caption_ids = blip_model.generate(
                **blip_inputs, 
                max_new_tokens=max_length,
                num_beams=num_beams,
                early_stopping=True
            )
            caption = blip_processor.batch_decode(caption_ids, skip_special_tokens=True)[0]
        return caption

    # Generate caption button
    if uploaded_image is not None:
        st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
        st.write("Click below to generate a caption for your image.")

        if st.button("GENERATE CAPTION", key="generate_button", help="Generate a caption for the uploaded image"):
            try:
                with st.spinner("Extracting features..."):  # No text_color argument
                    features = extract_features(uploaded_image)
                
                with st.spinner("Generating caption..."):  # No text_color argument
                    caption = generate_caption(uploaded_image)
                    
                    # Convert the caption to uppercase
                    formatted_caption = caption.upper()
                    
                    # Display the caption in darker blue
                    st.markdown(f"<h2 style='font-weight:bold; font-size:32px; color:#0033cc;'>{formatted_caption}</h2>", unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"An error occurred: {e}")

# Create a Flask API
app = Flask(__name__)

# Define API endpoints
@app.route('/caption', methods=['POST'])
def generate_caption_api():
    image = request.files['image']
    caption = generate_caption(image)
    return jsonify({'caption': caption})

if __name__ == '__main__':
    app.run(debug=True)
