import os
import argparse
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "04_business_money_leak (2)", "04_business_money_leak")

def load_data():
    customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"))
    products = pd.read_csv(os.path.join(DATA_DIR, "products.csv"))
    transactions = pd.read_csv(os.path.join(DATA_DIR, "transactions.csv"))

    tx = transactions.merge(products, on='product_id', how='left').merge(customers, on='customer_id', how='left')
    tx['is_problematic'] = tx['status'].isin(['Cancelled', 'Returned']).astype(int)

    # Feature engineering
    tx['unit_margin'] = tx['unit_price'] - tx['unit_cost']
    tx['is_upside_down'] = (tx['unit_cost'] > tx['list_price']).astype(int)
    tx['effective_price'] = tx['unit_price'] * (1 - tx['discount_pct'])

    features = [
        'quantity', 'unit_price', 'discount_pct', 'unit_cost', 'unit_margin',
        'is_upside_down', 'effective_price', 'supplier_lead_days',
        'category', 'channel', 'payment_method', 'region', 'customer_segment'
    ]

    X = pd.get_dummies(tx[features], drop_first=True)
    y = tx['is_problematic']

    return X, y

def train_pytorch(max_epochs=30, patience=20, weighted=False):
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader

    print(f"\n" + "="*60)
    print(f"  PYTORCH NEURAL NETWORK TRAINING")
    print(f"  Configuration: Max Epochs = {max_epochs} | Early Stopping Patience = {patience}")
    print("="*60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")

    X, y = load_data()
    X_train_raw, X_val_raw, y_train_raw, y_val_raw = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_val = scaler.transform(X_val_raw)

    y_train = y_train_raw.values
    y_val = y_val_raw.values

    # Loss function: Standard BCE produces true unscaled cross-entropy loss (~0.46 vs ~1.15)
    if weighted:
        pos_weight = float((len(y_train) - sum(y_train)) / sum(y_train))
        criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]).to(device))
    else:
        criterion = nn.BCEWithLogitsLoss()

    train_dataset = TensorDataset(torch.tensor(X_train, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32).unsqueeze(1))
    val_dataset = TensorDataset(torch.tensor(X_val, dtype=torch.float32), torch.tensor(y_val, dtype=torch.float32).unsqueeze(1))

    train_loader = DataLoader(train_dataset, batch_size=256, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=512, shuffle=False)

    class TransactionRiskNet(nn.Module):
        def __init__(self, input_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.BatchNorm1d(128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.BatchNorm1d(64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 1)
            )

        def forward(self, x):
            return self.net(x)

    model = TransactionRiskNet(X_train.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    best_val_loss = float('inf')
    epochs_no_improve = 0
    best_weights_path = os.path.join(BASE_DIR, "best_model_weights.pt")

    for epoch in range(1, max_epochs + 1):
        # Training
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            preds = model(batch_x)
            loss = criterion(preds, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * batch_x.size(0)
        train_loss /= len(train_loader.dataset)

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds_list = []
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                preds = model(batch_x)
                loss = criterion(preds, batch_y)
                val_loss += loss.item() * batch_x.size(0)
                val_preds_list.extend(torch.sigmoid(preds).cpu().numpy().flatten())
        val_loss /= len(val_loader.dataset)
        val_auc = roc_auc_score(y_val, val_preds_list)

        print(f"Epoch [{epoch:02d}/{max_epochs:02d}] - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val ROC-AUC: {val_auc:.4f}", end="")

        # Check early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            epochs_no_improve = 0
            torch.save(model.state_dict(), best_weights_path)
            print("  --> [Best Model Saved]")
        else:
            epochs_no_improve += 1
            print(f"  (no improvement for {epochs_no_improve}/{patience} epochs)")

        if epochs_no_improve >= patience:
            print(f"\n[!] Early stopping triggered at Epoch {epoch}! Validation loss didn't improve for {patience} consecutive epochs.")
            break

    print(f"\nTraining completed! Best Validation Loss: {best_val_loss:.4f}")
    if os.path.exists(best_weights_path):
        model.load_state_dict(torch.load(best_weights_path, weights_only=True))
        print(f"Loaded best checkpoint from: {best_weights_path}")

def train_xgboost(max_epochs=30, patience=20):
    import xgboost as xgb

    print(f"\n" + "="*60)
    print(f"  XGBOOST GRADIENT BOOSTING TRAINING")
    print(f"  Configuration: Max Epochs/Trees = {max_epochs} | Early Stopping Rounds = {patience}")
    print("="*60)

    X, y = load_data()
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scale_pos_weight = float((len(y_train) - sum(y_train)) / sum(y_train))

    model = xgb.XGBClassifier(
        n_estimators=max_epochs,
        early_stopping_rounds=patience,
        eval_metric='logloss',
        scale_pos_weight=scale_pos_weight,
        learning_rate=0.08,
        max_depth=5,
        random_state=42
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_val, y_val)],
        verbose=True
    )

    val_probs = model.predict_proba(X_val)[:, 1]
    val_preds = model.predict(X_val)
    auc = roc_auc_score(y_val, val_probs)

    print(f"\nTraining complete!")
    print(f"Best Iteration/Epoch: {model.best_iteration}")
    print(f"Validation ROC-AUC: {auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_val, val_preds, zero_division=0))

    model_path = os.path.join(BASE_DIR, "best_xgboost_model.json")
    model.save_model(model_path)
    print(f"Saved trained XGBoost model to: {model_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ML model with 30 epochs and early stopping at 20")
    parser.add_argument("--model", choices=["xgboost", "pytorch"], default="xgboost", help="Model type to train (xgboost or pytorch)")
    parser.add_argument("--epochs", type=int, default=30, help="Maximum epochs / iterations (default: 30)")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience rounds (default: 20)")
    parser.add_argument("--weighted", action="store_true", help="Apply class penalty weighting (shifts loss scale from ~0.46 to ~1.15)")

    args = parser.parse_args()

    if args.model == "pytorch":
        train_pytorch(max_epochs=args.epochs, patience=args.patience, weighted=args.weighted)
    else:
        train_xgboost(max_epochs=args.epochs, patience=args.patience)
