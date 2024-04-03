# -*- coding: utf-8 -*-
"""convnet-vgg16.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/rasbt/deeplearning-models/blob/master/pytorch_ipynb/cnn/cnn-resnet34-mnist.ipynb

Deep Learning Models -- A collection of various deep learning architectures, models, and tips for TensorFlow and PyTorch in Jupyter Notebooks.
- Author: Sebastian Raschka
- GitHub Repository: https://github.com/rasbt/deeplearning-models
"""

# Commented out IPython magic to ensure Python compatibility.
# %load_ext watermark
# %watermark -a 'Sebastian Raschka' -v -p torch

"""# Model Zoo -- ResNet-34 MNIST Digits Classifier

### Network Architecture

The network in this notebook is an implementation of the ResNet-34 [1] architecture on the MNIST digits dataset (http://yann.lecun.com/exdb/mnist/) to train a handwritten digit classifier.  


References
    
- [1] He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. In Proceedings of the IEEE conference on computer vision and pattern recognition (pp. 770-778). ([CVPR Link](https://www.cv-foundation.org/openaccess/content_cvpr_2016/html/He_Deep_Residual_Learning_CVPR_2016_paper.html))

- [2] http://yann.lecun.com/exdb/mnist/

![](https://github.com/rasbt/deeplearning-models/blob/master/pytorch_ipynb/images/resnets/resnet34/resnet34-arch.png?raw=1)

The following figure illustrates residual blocks with skip connections such that the input passed via the shortcut matches the dimensions of the main path's output, which allows the network to learn identity functions.

![](https://github.com/rasbt/deeplearning-models/blob/master/pytorch_ipynb/images/resnets/resnet-ex-1-1.png?raw=1)


The ResNet-34 architecture actually uses residual blocks with skip connections such that the input passed via the shortcut matches is resized to dimensions of the main path's output. Such a residual block is illustrated below:

![](https://github.com/rasbt/deeplearning-models/blob/master/pytorch_ipynb/images/resnets/resnet-ex-1-2.png?raw=1)

For a more detailed explanation see the other notebook, [resnet-ex-1.ipynb](resnet-ex-1.ipynb).

## Imports
"""

import os
import time

import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from torchvision import datasets
from torchvision import transforms

import matplotlib.pyplot as plt
from PIL import Image


if torch.cuda.is_available():
    torch.backends.cudnn.deterministic = True

"""## Model Settings"""

##########################
### SETTINGS
##########################

# Hyperparameters
RANDOM_SEED = 1
LEARNING_RATE = 0.001
BATCH_SIZE = 128
NUM_EPOCHS = 10

# Architecture
NUM_FEATURES = 28*28
NUM_CLASSES = 10

# Other
DEVICE = "cuda:0"
GRAYSCALE = True

"""### MNIST Dataset"""

##########################
### MNIST DATASET
##########################

# Note transforms.ToTensor() scales input images
# to 0-1 range
train_dataset = datasets.MNIST(root='data',
                               train=True,
                               transform=transforms.ToTensor(),
                               download=True)

test_dataset = datasets.MNIST(root='data',
                              train=False,
                              transform=transforms.ToTensor())


train_loader = DataLoader(dataset=train_dataset,
                          batch_size=BATCH_SIZE,
                          shuffle=True)

test_loader = DataLoader(dataset=test_dataset,
                         batch_size=BATCH_SIZE,
                         shuffle=False)

# Checking the dataset
for images, labels in train_loader:
    print('Image batch dimensions:', images.shape)
    print('Image label dimensions:', labels.shape)
    break

device = torch.device(DEVICE)
torch.manual_seed(0)

for epoch in range(2):

    for batch_idx, (x, y) in enumerate(train_loader):

        print('Epoch:', epoch+1, end='')
        print(' | Batch index:', batch_idx, end='')
        print(' | Batch size:', y.size()[0])

        x = x.to(device)
        y = y.to(device)
        break

"""The following code cell that implements the ResNet-34 architecture is a derivative of the code provided at https://pytorch.org/docs/0.4.0/_modules/torchvision/models/resnet.html."""

##########################
### MODEL
##########################


def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = conv3x3(planes, planes)
        self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out




class ResNet(nn.Module):

    def __init__(self, block, layers, num_classes, grayscale):
        self.inplanes = 64
        if grayscale:
            in_dim = 1
        else:
            in_dim = 3
        super(ResNet, self).__init__()
        self.conv1 = nn.Conv2d(in_dim, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AvgPool2d(7, stride=1)
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, (2. / n)**.5)
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes, planes * block.expansion,
                          kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        # because MNIST is already 1x1 here:
        # disable avg pooling
        #x = self.avgpool(x)

        x = x.view(x.size(0), -1)
        logits = self.fc(x)
        probas = F.softmax(logits, dim=1)
        return logits, probas



def resnet34(num_classes):
    """Constructs a ResNet-34 model."""
    model = ResNet(block=BasicBlock,
                   layers=[3, 4, 6, 3],
                   num_classes=NUM_CLASSES,
                   grayscale=GRAYSCALE)
    return model

torch.manual_seed(RANDOM_SEED)
model = resnet34(NUM_CLASSES)
model.to(DEVICE)

optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

"""## Training with CutMix"""

# Commented out IPython magic to ensure Python compatibility.import torch
import time
import os

import torch
from art.defences.preprocessor import FeatureSqueezing

# Initialize Feature Squeezing
feature_squeezing = FeatureSqueezing(clip_values=(0, 1), bit_depth=1)

device = torch.device("cuda:0")  # Use GPU
model.to(device)
criterion = torch.nn.CrossEntropyLoss()

model_file_path = "FeatureSqueezing.pth"

# Check if the model file exists; if so, load it
if os.path.isfile(model_file_path):
    model.load_state_dict(torch.load(model_file_path))
    print("Model loaded.")

# Training loop
for epoch in range(NUM_EPOCHS):
    # Your training process here
    model.train()
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        inputs, targets = inputs.to(device), targets.to(device)

        # Convert inputs to numpy arrays for feature squeezing
        inputs_np = inputs.cpu().numpy()

        # Apply Feature Squeezing
        squeezed_inputs_np, _ = feature_squeezing(inputs_np)

        # Convert squeezed inputs back to PyTorch tensors and move to the correct device
        squeezed_inputs = torch.tensor(squeezed_inputs_np).to(device)

        # Forward pass
        outputs, _ = model(squeezed_inputs)  # Ensure this line matches your model's output

        # Calculate loss
        loss = criterion(outputs, targets)

        # Backward pass and optimize
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_idx % 100 == 0:
            print(f'Epoch [{epoch+1}/{NUM_EPOCHS}], Step [{batch_idx+1}/{len(train_loader)}], Loss: {loss.item():.4f}')
    # Save the model after each epoch
    torch.save(model.state_dict(), model_file_path)
    print(f"Model saved after Epoch {epoch+1}.")


    

"""## Evaluation"""

model.eval()  # Set the model to evaluation mode
correct = 0
total = 0

with torch.no_grad():  # Inference mode, no gradients needed
    for inputs, targets in test_loader:
        inputs, targets = inputs.to(device), targets.to(device)
        outputs, _ = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += targets.size(0)
        correct += (predicted == targets).sum().item()

accuracy = 100 * correct / total
print(f'Accuracy of the model on the test images: {accuracy:.2f}%')

#Importing Adversarial attacks
from art.estimators.classification import PyTorchClassifier
from art.attacks.evasion import FastGradientMethod, ProjectedGradientDescent

class ModelWrapper(nn.Module):
    def __init__(self, model):
        super(ModelWrapper, self).__init__()
        self.model = model

    def forward(self, x):
        logits, _ = self.model(x)  # Assuming the model returns logits and probabilities
        return logits

model.eval()  # Set the model to evaluation mode


wrapped_model = ModelWrapper(model)

# Wrap the PyTorch model with ART's PyTorchClassifier
classifier = PyTorchClassifier(
    model=wrapped_model,
    clip_values=(0, 1),
    loss=torch.nn.CrossEntropyLoss(),
    optimizer=optimizer,
    input_shape=(1, 28, 28),
    nb_classes=NUM_CLASSES,
    device_type=DEVICE
)

"""#FAST GRADIENT SIGN METHOD """

total_correct = 0
total_examples = 0

# Create FGSM attack
fgsm_attack = FastGradientMethod(estimator=classifier, eps=0.2)

# Ensure the model is in evaluation mode
model.eval()

for images, labels in test_loader:
    # Convert images to NumPy array for ART
    images_np = images.numpy()

    # Generate adversarial examples
    x_test_adv = fgsm_attack.generate(x=images_np)

    # Convert adversarial examples back to PyTorch tensors and move to the correct device
    x_test_adv_torch = torch.from_numpy(x_test_adv).to(DEVICE)
    labels = labels.to(DEVICE)

    # Perform inference on adversarial examples
    logits, _ = model(x_test_adv_torch)
    _, predictions = torch.max(logits, dim=1)

    # Update the accumulators
    total_correct += (predictions == labels).sum().item()
    total_examples += labels.size(0)

# Calculate the overall accuracy
accuracy_fgsm = total_correct / total_examples
print(f"Accuracy on FGSM adversarial examples over the entire test set after using Feature Squeezing: {accuracy_fgsm * 100:.2f}%")

"""#PROJECT GRADIENT DESCENT"""
import time
total_correct = 0
total_examples = 0

# Create PGD attack
pgd_attack = ProjectedGradientDescent(estimator=classifier, eps=0.1, max_iter=40)

# Ensure the model is in evaluation mode
model.eval()

#Starting time
start_time = time.time()

for images, labels in test_loader:
    # Convert images to NumPy array for ART
    images_np = images.numpy()

    # Generate adversarial examples with PGD
    x_test_adv_pgd = pgd_attack.generate(x=images_np)

    # Convert adversarial examples to torch tensors and move to the correct device
    x_test_adv_pgd_torch = torch.from_numpy(x_test_adv_pgd).to(DEVICE)
    labels = labels.to(DEVICE)

    # Perform inference on adversarial examples
    logits, _ = model(x_test_adv_pgd_torch)
    _, predictions = torch.max(logits, dim=1)

    # Update the accumulators
    total_correct += (predictions == labels).sum().item()
    total_examples += labels.size(0)

#End Timer
end_time = time.time()
# Calculate the overall accuracy
accuracy_pgd = total_correct / total_examples
print(f"Accuracy on PGD adversarial examples over the entire test set after using Feature Squeezing: {accuracy_pgd * 100:.2f}%")

#Total time
total_time = end_time- start_time
print(f"Total time required: {total_time:.2f} seconds")

# Commented out IPython magic to ensure Python compatibility.
# %watermark -iv
