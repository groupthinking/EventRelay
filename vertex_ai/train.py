
import argparse
import logging
import os

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train(args):
    logger.info("Starting training...")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    
    # Dummy data for demonstration
    x = torch.randn(100, 10)
    y = torch.randint(0, 2, (100,))
    dataset = TensorDataset(x, y)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    
    # Simple model
    model = nn.Sequential(
        nn.Linear(10, 50),
        nn.ReLU(),
        nn.Linear(50, 2)
    )
    
    if torch.cuda.is_available():
        model = model.cuda()
        logger.info("Model moved to GPU")

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(model.parameters(), lr=args.learning_rate)
    
    for epoch in range(args.epochs):
        for batch_x, batch_y in dataloader:
            if torch.cuda.is_available():
                batch_x, batch_y = batch_x.cuda(), batch_y.cuda()
                
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
        
        logger.info(f"Epoch {epoch+1}/{args.epochs}, Loss: {loss.item()}")

    # Save model artifact
    model_path = "model.pth"
    torch.save(model.state_dict(), model_path)
    logger.info(f"Model saved to {model_path}")
    
    # TODO: Upload to GCS using args.model_dir if provided
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=5, help='Number of epochs to run')
    parser.add_argument('--batch_size', type=int, default=32, help='Batch size')
    parser.add_argument('--learning_rate', type=float, default=0.01, help='Learning rate')
    parser.add_argument('--model_dir', type=str, help='Output directory for model artifacts')
    
    args = parser.parse_args()
    train(args)
