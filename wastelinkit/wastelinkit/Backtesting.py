import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import tensorflow as tf


# Simulated data for one district (Replace with your actual cleaned dataset)
df = pd.read_csv("tn_realistic_plastic_waste_2018_2024.csv")
df['Month'] = pd.to_datetime(df['Month'])

months = pd.date_range(start='2018-01-01', end='2024-12-01', freq='MS')
districts = ['Chennai']
plastic_types = ['PET_Tons', 'HDPE_Tons', 'PVC_Tons', 'LDPE_Tons', 'PP_Tons', 'PS_Tons']

df['Month'] = pd.to_datetime(df['Month'])

# Use Chennai data for testing
district_df = df[df['District'] == 'Chennai'].copy()
district_df.set_index('Month', inplace=True)

# Scale features
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(district_df[plastic_types])

# Train on Jan 2018 – Dec 2023
train_size = len(pd.date_range('2018-01-01', '2023-12-01', freq='MS'))
sequence_length = 12

X_train, y_train = [], []
for i in range(sequence_length, train_size):
    X_train.append(scaled_data[i-sequence_length:i])
    y_train.append(scaled_data[i])

X_train, y_train = np.array(X_train), np.array(y_train)


model = Sequential([
    LSTM(64, activation='relu', return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
    LSTM(32, activation='relu'),
    Dense(len(plastic_types))
])




model.compile(optimizer=Adam(learning_rate=0.0005), loss='mse')

from tensorflow.keras.callbacks import EarlyStopping

early_stop = EarlyStopping(monitor='loss', patience=30, restore_best_weights=True)
model.fit(X_train, y_train, epochs=1000, verbose=0, callbacks=[early_stop])



# Predict Jan–June 2024 using last 12 months of 2023
test_start = train_size
predictions = []
input_seq = scaled_data[test_start-sequence_length:test_start]

for _ in range(6):
    input_reshaped = input_seq.reshape(1, sequence_length, len(plastic_types))
    pred = model.predict(input_reshaped, verbose=0)[0]
    predictions.append(pred)
    input_seq = np.vstack([input_seq[1:], pred])

# Convert predictions back to actual scale
predicted_values = scaler.inverse_transform(predictions)
actual_values = district_df.loc['2024-01-01':'2024-06-01'][plastic_types].values

# Metrics
mse = mean_squared_error(actual_values, predicted_values)
mae = mean_absolute_error(actual_values, predicted_values)

# Plot comparison for PET
months_pred = pd.date_range(start='2024-01-01', periods=6, freq='MS')
plt.figure(figsize=(10, 5))
plt.plot(months_pred, actual_values[:, 0], marker='o', label='Actual PET')
plt.plot(months_pred, predicted_values[:, 0], marker='x', label='Predicted PET')
plt.title('Backtest: PET Plastic Waste Prediction (Jan–June 2024)')
plt.xlabel('Month')
plt.ylabel('PET Tons')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

print("MSE:", mse)
print("MAE:", mae)