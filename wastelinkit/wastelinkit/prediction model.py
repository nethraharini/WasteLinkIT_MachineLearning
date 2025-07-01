import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import datetime

# Load dataset
df = pd.read_csv("tn_realistic_plastic_waste_2018_2024.csv")
df['Month'] = pd.to_datetime(df['Month'])
df = df.sort_values(['District', 'Month'])


# Sequence generator
def create_sequences(data, n_steps):
    X, y = [], []
    for i in range(n_steps, len(data)):
        X.append(data[i - n_steps:i])
        y.append(data[i])
    return np.array(X), np.array(y)


# LSTM settings
n_steps = 6
features = ['PET_Tons', 'HDPE_Tons', 'PVC_Tons', 'LDPE_Tons', 'PP_Tons', 'PS_Tons']
districts = df['District'].unique()

district_predictions = {}

for district in districts:
    print(f"\n📈 Training model for: {district}")

    # Get district data
    df_district = df[df['District'] == district].copy()
    df_district.set_index('Month', inplace=True)

    # Normalize
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(df_district[features])

    # Create sequences
    X, y = create_sequences(data_scaled, n_steps)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Reshape for LSTM: [samples, time steps, features]
    X_train = X_train.reshape((X_train.shape[0], n_steps, len(features)))
    X_test = X_test.reshape((X_test.shape[0], n_steps, len(features)))

    # Build LSTM
    model = Sequential()
    model.add(LSTM(64, activation='relu', input_shape=(n_steps, len(features))))
    model.add(Dense(64, activation='relu'))
    model.add(Dense(len(features)))
    model.compile(optimizer='adam', loss='mse')

    # Fit model
    model.fit(X_train, y_train, epochs=50, verbose=0)

    # Predict next month
    last_seq = data_scaled[-n_steps:]
    last_seq = last_seq.reshape((1, n_steps, len(features)))

    pred_scaled = model.predict(last_seq)
    pred_actual = scaler.inverse_transform(pred_scaled)[0]

    import datetime

    # Get the predicted month (e.g., Jan 2025)
    last_date = df_district.index[-1]
    predicted_month = (last_date + pd.DateOffset(months=1)).strftime('%b %Y')

    # Print the predictions
    print(f"\n📅 Predicted Plastic Waste Output for: {district} - {predicted_month}")
    for plastic_type, value in zip(features, pred_actual):
        print(f"{plastic_type}: {value:.2f} tons")


    # Save result
    district_predictions[district] = dict(zip(features, pred_actual))

# Convert to DataFrame
result_df = pd.DataFrame.from_dict(district_predictions, orient='index')
result_df.index.name = 'District'
# 👇 Add this line to show all columns
from tabulate import tabulate

print("\n✅ Predicted next-month plastic waste by district:\n")
print(tabulate(result_df.round(2), headers='keys', tablefmt='psql'))





# Optional: plot one district
district_to_plot = "Chennai"
plt.figure(figsize=(10, 6))
plt.bar(features, district_predictions[district_to_plot].values(), color='skyblue')
plt.title(f"Next Month Plastic Waste Prediction - {district_to_plot}")
plt.ylabel("Tons")
plt.grid(True)
plt.show()
