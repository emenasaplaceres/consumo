import streamlit as st
import pandas as pd
import zipfile
import os
import plotly.graph_objects as go
from datetime import datetime, time

# Configurar la página para un diseño amplio
st.set_page_config(layout="wide")

# Columnas parametrizables
TIMESTAMP_COL = 'Local Time Stamp'
CONSUMPTION_COL = 'Active energy (Wh)'

def extract_zip(uploaded_zip):
    with zipfile.ZipFile(uploaded_zip, 'r') as z:
        z.extractall('temp_dir')
    return [f for f in os.listdir('temp_dir') if f.endswith('.csv')]

import io
def read_csv_with_timestamp_autodetect(file_buffer):
    # Leemos todo el archivo en memoria como bytes
    file_bytes = file_buffer.read()
    
    # Creamos un objeto io.BytesIO para poder leerlo múltiples veces
    file_buffer = io.BytesIO(file_bytes)
    
    # Intentamos detectar el delimitador
    file_sample = file_buffer.read(1024).decode()
    delimiter = ',' if ',' in file_sample else '\t'

    print(f'{delimiter=}')
    
    # Creamos otro objeto io.BytesIO para poder leerlo de nuevo
    file_buffer = io.BytesIO(file_bytes)

    # Buscamos la fila que contiene el TIMESTAMP_COL
    skiprows = None
    for i, line in enumerate(pd.read_csv(file_buffer, delimiter=delimiter, chunksize=1, header=None)):
        print(line.values)
        if TIMESTAMP_COL in line.values:
            skiprows = i
            break
            
    if skiprows is None:
        raise ValueError(f"The required column {TIMESTAMP_COL} was not found in the CSV file.")
        
    # Creamos otro objeto io.BytesIO para poder leerlo de nuevo
    file_buffer = io.BytesIO(file_bytes)
    
    return pd.read_csv(file_buffer, delimiter=delimiter, skiprows=skiprows+1, parse_dates=[TIMESTAMP_COL])



uploaded_file = st.file_uploader("Sube un archivo ZIP o CSV", type=['zip', 'csv'])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.zip'):
        csv_files = extract_zip(uploaded_file)
        selected_csv = st.selectbox("Selecciona un archivo CSV", csv_files)
        selected_csv_path = os.path.join('temp_dir', selected_csv)
        with open(selected_csv_path, 'rb') as f:
            df = read_csv_with_timestamp_autodetect(f)
    else:
        df = read_csv_with_timestamp_autodetect(uploaded_file)

    print(df.columns)
    
    min_datetime = df[TIMESTAMP_COL].min().to_pydatetime()
    max_datetime = df[TIMESTAMP_COL].max().to_pydatetime()
    min_date = min_datetime.date()
    max_date = max_datetime.date()

    st.write("#### Selecciona un rango de fechas y horas para calcular el consumo total:")
    col1, col2 = st.columns([1,1])
    with col1:
        start_date = st.date_input("Fecha de inicio", min_value=min_date, max_value=max_date, value=min_date)
        start_time = st.time_input("Hora de inicio", value=time(0, 0))
    with col2:
        end_date = st.date_input("Fecha de fin", min_value=min_date, max_value=max_date, value=max_date)
        end_time = st.time_input("Hora de fin", value=time(23, 59))

    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    if start_datetime < end_datetime:
        mask = (df[TIMESTAMP_COL] >= start_datetime) & (df[TIMESTAMP_COL] <= end_datetime)
        selected_data = df.loc[mask, CONSUMPTION_COL]
        total_consumption_delta = (selected_data.max() - selected_data.min()) / 1000.0  # Convert to kWh

        st.write(f"**Inicio ({start_datetime}): {selected_data.iloc[0]/1000:.3f} kWh**")
        st.write(f"**Fin ({end_datetime}): {selected_data.iloc[-1]/1000:.3f} kWh**")
        st.write(f"**Consumo total: {total_consumption_delta:.3f} kWh**")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df[TIMESTAMP_COL], y=df[CONSUMPTION_COL], mode='lines', name='Rango Completo', line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df.loc[mask, TIMESTAMP_COL], y=df.loc[mask, CONSUMPTION_COL], mode='lines', name='Rango Seleccionado', line=dict(color='red')))
        fig.update_layout(xaxis_title='Tiempo', yaxis_title='Consumo (Wh)', width=1600, height=600)
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, height=1000, use_container_width=True)
    else:
        st.error("Error: La fecha y hora de inicio deben ser anteriores a la fecha y hora de fin.")
