class MLSignal:
    def predict(self, features) -> float:
        return self.model.predict_proba(features)[1]
