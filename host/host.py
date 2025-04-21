import os

def main():
    print("Host ativo. Testando ping para roteadores...")
    os.system("ping -c 3 router1 || ping -c 3 router2 || ping -c 3 router3")

if __name__ == "__main__":
    main()
