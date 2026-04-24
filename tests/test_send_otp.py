import requests


def main():
    url = "https://underline-steersman-crepe.ngrok-free.dev/send-register-otp"
    data = {"email": "mailcuaban@gmail.com"}

    response = requests.post(url, json=data, timeout=10)

    print("STATUS:", response.status_code)
    print("TEXT:", response.text)


if __name__ == "__main__":
    main()
