
def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count


def get_user_name(user):
    return user["name"].upper()


def main():
    numbers = [10, 20, 30, 40]
    average = calculate_average(numbers)
    print("Average:", average)

    print("Empty list average:", calculate_average([]))

    user = {"username": "Chiamaka"}
    print("User:", get_user_name(user))


if __name__ == "__main__":
    main()
