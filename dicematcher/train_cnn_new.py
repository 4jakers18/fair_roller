#!/usr/bin/env python3
# dice_cnn_custom.py  – simple CNN for numeral D6 face recognition
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models, optimizers
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

# ==============================================================
#                  CONFIGURABLE HYPER-PARAMETERS
# ==============================================================
TRAIN_DIR            = "new_dataset/train"
VAL_DIR              = "new_dataset/valid"

IMG_SIZE             = (150, 150)          # ← was 256×256; 150×150 is what the ‘better’ model used
BATCH_SIZE           = 30                  # ← up from 16
EPOCHS_HEAD          = 50                  # training length
LEARNING_RATE        = 2e-4

# Augmentation – mirrors the notebook settings
AUG_ROT              = 360
AUG_WIDTH_SHIFT      = 0.10
AUG_HEIGHT_SHIFT     = 0.10
AUG_ZOOM             = (0.70, 1.10)
AUG_BRIGHTNESS       = (0.70, 1.20)
AUG_HFLIP            = False               # dice numerals -> flipping left/right changes class!
AUG_VFLIP            = False

MODEL_BEST_PATH      = "best_dice_cnn.h5"  # Checkpoint
MODEL_FINAL_PATH     = "dice_cnn_custom.h5"

# ==============================================================
#                         DATA PIPELINE
# ==============================================================
train_datagen = ImageDataGenerator(
    rotation_range=AUG_ROT,
    width_shift_range=AUG_WIDTH_SHIFT,
    height_shift_range=AUG_HEIGHT_SHIFT,
    zoom_range=AUG_ZOOM,
    brightness_range=AUG_BRIGHTNESS
)
val_datagen = ImageDataGenerator()     # no augmentation for validation

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

# ==============================================================
#                   CUSTOM CNN ARCHITECTURE
#   (exactly the block-stack from the notebook)
# ==============================================================
model = models.Sequential([
    layers.Conv2D(32 , (3,3), padding="same", activation="relu",
                  input_shape=IMG_SIZE + (3,)),
    layers.MaxPooling2D((2,2)),

    layers.Conv2D(64 , (3,3), padding="same", activation="relu"),
    layers.MaxPooling2D((2,2)),

    layers.Conv2D(128, (3,3), padding="same", activation="relu"),
    layers.MaxPooling2D((2,2)),

    layers.Conv2D(256, (3,3), padding="same", activation="relu"),
    layers.MaxPooling2D((2,2)),

    layers.Conv2D(512, (3,3), padding="same", activation="relu"),
    layers.MaxPooling2D((2,2)),

    layers.Flatten(),
    layers.Dense(train_gen.num_classes, activation="softmax")
])

model.summary()

# ==============================================================
#                       COMPILE & CALLBACKS
# ==============================================================
model.compile(
    optimizer=optimizers.Adam(learning_rate=LEARNING_RATE),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

callbacks = [
    EarlyStopping(monitor="val_accuracy", patience=12, restore_best_weights=True),
    ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=3),
    ModelCheckpoint(MODEL_BEST_PATH, monitor="val_accuracy",
                    save_best_only=True, verbose=1)
]

# ==============================================================
#                             TRAIN
# ==============================================================
history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS_HEAD,
    callbacks=callbacks
)

# ==============================================================
#                 SAVE MODEL & TRAINING PLOT
# ==============================================================
model.save(MODEL_FINAL_PATH)
print(f"✓ Final model saved to {MODEL_FINAL_PATH}")

plt.figure()
plt.plot(history.history["val_accuracy"], label="Validation Accuracy")
plt.title("Validation Accuracy vs Epochs")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.legend()
plt.tight_layout()
plt.savefig("val_accuracy_custom.png")
print("✓ Plot saved to val_accuracy_custom.png")
