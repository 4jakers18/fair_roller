#!/usr/bin/env python3
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

# =====================
#   CONFIGURABLE HYPERPARAMETERS
# =====================
TRAIN_DIR            = "new_dataset/train"
VAL_DIR              = "new_dataset/valid"
IMG_SIZE             = (256, 256)   # MobileNetV2 expects 3 channels, but we set color_mode="rgb"
BATCH_SIZE           = 16
EPOCHS               = 50
ROTATION_RANGE       = 90
WIDTH_SHIFT_RANGE    = 0.1
HEIGHT_SHIFT_RANGE   = 0.1
ZOOM_RANGE           = 0.1
BRIGHTNESS_RANGE     = (0.9, 1.1)
HORIZONTAL_FLIP      = False
VERTICAL_FLIP        = False
OPTIMIZER_NAME       = "adam"
LEARNING_RATE        = 1e-4           # often lower for finetuning
MODEL_PATH           = "dice_mobilenetv2.h5"

# =====================
#   DATA GENERATORS
# =====================
# We load as RGB so that grayscale crops are automatically duplicated into 3‐channels
train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,  # MobileNetV2-style normalization
    rotation_range=ROTATION_RANGE,
    width_shift_range=WIDTH_SHIFT_RANGE,
    height_shift_range=HEIGHT_SHIFT_RANGE,
    zoom_range=ZOOM_RANGE,
    brightness_range=BRIGHTNESS_RANGE,
    horizontal_flip=HORIZONTAL_FLIP,
    vertical_flip=VERTICAL_FLIP,
    validation_split=0.0  # we'll do separate folders
)
val_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input
)

train_gen = train_datagen.flow_from_directory(
    TRAIN_DIR,
    target_size=IMG_SIZE,
    color_mode="rgb",
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    shuffle=True
)
val_gen = val_datagen.flow_from_directory(
    VAL_DIR,
    target_size=IMG_SIZE,
    color_mode="rgb",
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    shuffle=False
)

# =====================
#   BUILD TRANSFER LEARNING MODEL
# =====================
# 1) Base backbone
backbone = MobileNetV2(
    input_shape=IMG_SIZE + (3,),
    include_top=False,
    weights="imagenet"
)
backbone.trainable = False  # freeze for initial training

# 2) New classifier head
model = models.Sequential([
    backbone,
    layers.GlobalAveragePooling2D(),
    layers.Dense(64, activation="relu"),
    layers.Dropout(0.3),
    layers.Dense(train_gen.num_classes, activation="softmax")
])

# =====================
#   COMPILE
# =====================
if OPTIMIZER_NAME == 'sgd':
    optimizer = optimizers.SGD(learning_rate=LEARNING_RATE, momentum=0.9)
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
#   CALLBACKS
# =====================
callbacks = [
    EarlyStopping(monitor="val_accuracy", patience=15, restore_best_weights=True),
    ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3)
]

# =====================
#   TRAIN HEAD ONLY
# =====================
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =====================
#   OPTIONAL: FINE‐TUNE BACKBONE
# =====================
# Unfreeze some of the top layers of the backbone for fine‐tuning
for layer in backbone.layers[-30:]:
    if not isinstance(layer, layers.BatchNormalization):
        layer.trainable = True

model.compile(
    optimizer=optimizers.Adam(learning_rate=LEARNING_RATE/10),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

ft_history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=20,
    callbacks=callbacks
)

# =====================
#   SAVE MODEL & PLOTS
# =====================
model.save(MODEL_PATH)
print(f"Model saved to {MODEL_PATH}")

plt.figure()
plt.plot(history.history['val_accuracy'] + ft_history.history['val_accuracy'], 
         label='Validation Accuracy')
plt.title('Val Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.legend()
plt.savefig('val_accuracy_tf.png')
