#!/usr/bin/env python3
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# =====================
#   CONFIGURABLE HYPERPARAMETERS
# =====================
DATA_DIR               = "dataset"        # dataset root directory
IMG_SIZE               = (256, 256)       # input image size
BATCH_SIZE             = 32                # training batch size
EPOCHS                 = 300                # number of training epochs
VALIDATION_SPLIT       = 0.3               # fraction reserved for validation
ROTATION_RANGE         = 45               # degrees for random rotations
WIDTH_SHIFT_RANGE      = 0.1               # horizontal shift fraction
HEIGHT_SHIFT_RANGE     = 0.1               # vertical shift fraction
ZOOM_RANGE             = 0.2               # zoom range fraction
BRIGHTNESS_RANGE       = (0.9, 1.1)        # brightness jitter range
HORIZONTAL_FLIP        = False             # allow horizontal flip
VERTICAL_FLIP          = False             # allow vertical flip
BINARIZE_PROBABILITY   = 0.0               # probability to apply thresholding
DROPOUT_RATE           = 0.0               # dropout rate after dense layer
OPTIMIZER_NAME         = "adam"           # 'adam', 'sgd', or 'rmsprop'
LEARNING_RATE          = 1e-3              # initial learning rate
MOMENTUM               = 0.9               # momentum for SGD
MODEL_PATH             = "dice_cnn.h5"   # filename to save the model

# =====================
#   PREPROCESS FUNCTION
# =====================
def preprocess_fn(img):
    """
    img: float32 array in [0,1], shape (H,W,1).
    Randomly binarize some images to emphasize shape.
    """
    gray = img[:, :, 0]
    if np.random.rand() < BINARIZE_PROBABILITY:
        gray = (gray > 0.5).astype(np.float32)
    return gray[..., np.newaxis]

# =====================
#   DATA GENERATORS
# =====================
train_datagen = ImageDataGenerator(
    rescale=1/255.0,
    preprocessing_function=preprocess_fn,
    validation_split=VALIDATION_SPLIT,
    rotation_range=ROTATION_RANGE,
    width_shift_range=WIDTH_SHIFT_RANGE,
    height_shift_range=HEIGHT_SHIFT_RANGE,
    zoom_range=ZOOM_RANGE,
    brightness_range=BRIGHTNESS_RANGE,
    horizontal_flip=HORIZONTAL_FLIP,
    vertical_flip=VERTICAL_FLIP
)

train_gen = train_datagen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    color_mode="grayscale",
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training",
    shuffle=True
)
val_gen = train_datagen.flow_from_directory(
    DATA_DIR,
    target_size=IMG_SIZE,
    color_mode="grayscale",
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

# =====================
#   BUILD MODEL
# =====================
model = models.Sequential([
    layers.Input(shape=IMG_SIZE + (1,)),
    layers.Conv2D(32, 3, activation="relu", padding="same"),
    layers.MaxPooling2D(),
    layers.Conv2D(64, 3, activation="relu", padding="same"),
    layers.MaxPooling2D(),
    layers.Conv2D(128, 3, activation="relu", padding="same"),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(DROPOUT_RATE),
    layers.Dense(train_gen.num_classes, activation="softmax")
])

# =====================
#   COMPILE MODEL
# =====================
if OPTIMIZER_NAME == 'sgd':
    optimizer = optimizers.SGD(learning_rate=LEARNING_RATE, momentum=MOMENTUM)
elif OPTIMIZER_NAME == 'rmsprop':
    optimizer = optimizers.RMSprop(learning_rate=LEARNING_RATE)
else:
    optimizer = optimizers.Adam(learning_rate=LEARNING_RATE)

model.compile(
    optimizer=optimizer,
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()




# =====================
#   TRAIN MODEL
# =====================
callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=20,
        restore_best_weights=True
    )
]
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    # callbacks=callbacks   # ← here
)


# =====================
#   SAVE MODEL
# =====================
model.save(MODEL_PATH)
print(f"Model saved to {MODEL_PATH}")

# =====================
#   PLOT TRAINING METRICS
# =====================
# Accuracy plot
plt.figure()
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Model Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
acc_plot = 'accuracy_plot.png'
plt.savefig(acc_plot)
print(f"Saved accuracy plot to {acc_plot}")

# Loss plot
plt.figure()
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
loss_plot = 'loss_plot.png'
plt.savefig(loss_plot)
print(f"Saved loss plot to {loss_plot}")
