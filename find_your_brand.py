# -*- coding: utf-8 -*-
"""find_your_brand.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1VOsl2D-9tU-cQ93ooDDBbDOYYxxTBdqe
"""

# 필요한 라이브러리 설치
pip install streamlit tensorflow matplotlib opencv-python gdown

# Streamlit 앱 코드
import streamlit as st
import os
import numpy as np
import cv2
import matplotlib.pyplot as plt
import gdown
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.applications.resnet50 import preprocess_input

# Google Drive 링크와 파일 ID 매핑
drive_links = {
    "chanel": "1-00AKEYIqEVER3KBMClAXoUilL6cuXKG",
    "dior": "1-3RaWXti8xUFxBeLz7ltWb_JCw73PuMc",
    "louis": "1-CEM6C6mqQDdbXmeLbq0wHArWXPBOOFt",
    "gucci": "1-Scddd_rUojfn-jHLT1OgZCDkMJXob2W",
    "prada": "1-SEeGlwPYWo_AvsjJ7d-minCv374bN8q",
    "ysl": "1-OGDPRbnWgmqmfFmuiWOW7unZkvDoio3",
}

# 모델 파일 다운로드 함수
def download_model_from_drive(file_id, output_path):
    url = f"https://drive.google.com/uc?id={file_id}"
    if not os.path.exists(output_path):
        st.write(f"{output_path} 다운로드 중...")
        gdown.download(url, output_path, quiet=False)
    return output_path

# 모델 다운로드 및 로드
MODEL_DIR = "models"  # 로컬 모델 저장 경로
os.makedirs(MODEL_DIR, exist_ok=True)

# 브랜드 리스트
BRANDS = ["chanel", "dior", "louis", "ysl", "prada", "gucci"]

# 각 브랜드 모델 다운로드 및 로드
models = {}
for brand, file_id in drive_links.items():
    model_path = os.path.join(MODEL_DIR, f"{brand}_model.h5")
    download_model_from_drive(file_id, model_path)
    models[brand] = load_model(model_path)

# Grad-CAM 함수
def generate_grad_cam(model, image, layer_name="conv5_block3_out"):
    import tensorflow as tf
    # 입력 이미지에 대한 예측 수행
    preds = model.predict(image)
    pred_index = np.argmax(preds[0])  # 모델이 예측한 클래스 인덱스

    # 합성곱 층의 출력과 예측 대상 클래스의 그래디언트 가져오기
    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(layer_name).output, model.output]
    )
    with tf.GradientTape() as tape:
        conv_output, predictions = grad_model(image)
        loss = predictions[:, pred_index]

    # 그래디언트 계산
    grads = tape.gradient(loss, conv_output)[0]

    # 각 필터의 중요도를 계산
    weights = tf.reduce_mean(grads, axis=(0, 1))
    cam = np.dot(conv_output[0], weights)

    # Grad-CAM 결과 시각화
    cam = cv2.resize(cam.numpy(), (224, 224))
    cam = np.maximum(cam, 0)
    heatmap = cam / cam.max()  # Normalize

    return heatmap, pred_index

# Grad-CAM 결과를 원본 이미지 위에 겹치기
def overlay_grad_cam(image, heatmap):
    heatmap = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
    heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(image, 0.6, heatmap, 0.4, 0)
    return overlay

# 입력 이미지 처리 함수
def process_input_image(image_path):
    img = load_img(image_path, target_size=(224, 224))
    img_array = img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

# Streamlit UI
st.title("브랜드 엠버서더 추천 시스템 (시각화 포함)")
st.write("5장의 이미지를 업로드하면, 어떤 브랜드와 가장 유사한지 분석하고 시각화합니다.")

# 이미지 업로드
uploaded_files = st.file_uploader("이미지를 업로드하세요 (최대 5장)", accept_multiple_files=True, type=["jpg", "jpeg", "png"])

if uploaded_files:
    # 업로드된 이미지를 화면에 표시
    st.write("업로드된 이미지:")
    input_images = []
    original_images = []
    for uploaded_file in uploaded_files:
        image = load_img(uploaded_file, target_size=(224, 224))
        st.image(image, caption=uploaded_file.name, width=150)
        input_images.append(process_input_image(uploaded_file))
        original_images.append(np.array(load_img(uploaded_file, target_size=(224, 224))))

    # 모델 로드 및 Grad-CAM 시각화
    for i, img in enumerate(input_images):
        st.write(f"### 이미지 {i+1}")
        heatmap_dict = {}
        for brand, model in models.items():
            # Grad-CAM 생성
            heatmap, _ = generate_grad_cam(model, img)
            overlay = overlay_grad_cam(original_images[i], heatmap)

            # Grad-CAM 결과 표시
            heatmap_dict[brand] = heatmap
            st.image(overlay, caption=f"{brand} 모델의 Grad-CAM 결과", use_column_width=True)

        # 전체 브랜드의 유사도 Heatmap 비교
        st.write("### 브랜드별 Grad-CAM 비교")
        fig, axs = plt.subplots(1, len(BRANDS), figsize=(15, 5))
        for j, brand in enumerate(BRANDS):
            axs[j].imshow(heatmap_dict[brand])
            axs[j].set_title(brand)
            axs[j].axis('off')
        st.pyplot(fig)
