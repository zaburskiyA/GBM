from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.tree import DecisionTreeRegressor



def score(clf, x, y):
    return roc_auc_score(y == 1, clf.predict_proba(x)[:, 1])


class Boosting:

    def __init__(
            self,
            base_model_params: dict = None,
            n_estimators: int = 10,
            learning_rate: float = 0.1,
            subsample: float = 0.3,
            early_stopping_rounds: int = None,
    ):
        self.base_model_class = DecisionTreeRegressor
        self.base_model_params: dict = {} if base_model_params is None else base_model_params

        self.n_estimators: int = n_estimators

        self.models: list = []
        self.gammas: list = []

        self.learning_rate: float = learning_rate
        self.subsample: float = subsample

        self.early_stopping_rounds: int = early_stopping_rounds
        if early_stopping_rounds is not None:
            self.validation_loss = np.full(self.early_stopping_rounds, np.inf)

        
        self.history = defaultdict(list)

        self.sigmoid = lambda x: 1 / (1 + np.exp(-x))
        self.loss_fn = lambda y, z: -np.log(self.sigmoid(y * z)).mean()
        self.loss_derivative = lambda y, z: -y * self.sigmoid(-y * z)

    def fit_new_base_model(self, x, y, predictions):
        sub_ind = np.random.choice(len(y), int(self.subsample * len(y)), replace=True)
        x_sub, y_sub, pred_sub = x[sub_ind], y[sub_ind], predictions[sub_ind]
        model = self.base_model_class(**self.base_model_params)
        grad = -self.loss_derivative(y_sub, pred_sub)
        model.fit(x_sub, grad)
        gamma = self.find_optimal_gamma(y, predictions, model.predict(x))
        self.gammas.append(gamma * self.learning_rate)
        self.models.append(model)

    def fit(self, x_train, y_train, x_valid, y_valid):
        """
        :param x_train: features array (train set)
        :param y_train: targets array (train set)
        :param x_valid: features array (validation set)
        :param y_valid: targets array (validation set)
        """

        train_predictions = np.zeros(y_train.shape[0])
        valid_predictions = np.zeros(y_valid.shape[0])

        for i in range(self.n_estimators):
            self.fit_new_base_model(x_train, y_train, train_predictions)
            if self.early_stopping_rounds is not None:
                valid_predictions += self.predict_proba(x_valid)[:, 1]
                loss = self.loss_fn(valid_predictions, y_valid)
                self.history['loss_on_val'].append(loss)
                if loss < np.min(self.validation_loss):
                    self.validation_loss = np.append(self.validation_loss[1:], loss)
                else:
                    break
            train_predictions = self.predict_proba(x_train)[:, 1]
            valid_predictions = self.predict_proba(x_valid)[:, 1]
        if self.plot:
            pass

    def predict_proba(self, x):
        res = np.zeros((x.shape[0], 2))
        for gamma, model in zip(self.gammas, self.models):
            res[:, 1] += gamma * model.predict(x)
        res[:, 0] = 1 - self.sigmoid(res[:, 1])
        res[:, 1] = self.sigmoid(res[:, 1])
        return res

    def find_optimal_gamma(self, y, old_predictions, new_predictions) -> float:
        gammas = np.linspace(start=0, stop=1, num=100)
        loss = [self.loss_fn(y, old_predictions + gamma * new_predictions) for gamma in gammas]

        return gammas[np.argmin(loss)]

    def score(self, x, y):
        return score(self, x, y)

    @property
    def feature_importances_(self):
        imports = [model.feature_importances_ for model in self.models]
        res = np.zeros(imports[0].shape)
        for i in imports:
            res += i
        return res / res.sum()



