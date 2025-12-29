class BasicEvent:
    @property
    def id(self):
        return self.ID

    @property
    def json_dict(self):
        result = {
            "id": self.ID,
        }

        if hasattr(self, "json_data"):
            result["data"] = self.json_data

        return result
