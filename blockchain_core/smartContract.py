import time
import logging  # <-- Import logging

logger = logging.getLogger(__name__)  # <-- Lấy logger cho module này


class SmartContract:
    def __init__(self, sender, receiver, amount, deadline):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.deadline = deadline
        self.executed = False
        logger.info(
            f"Smart Contract được tạo: từ {self.sender[:10]}... đến {self.receiver[:10]}... Amount: {self.amount}, Deadline: {time.ctime(self.deadline)}")

    def execute(self, current_time):
        if self.executed:
            logger.info("Hợp đồng đã thực hiện rồi. Không thể thực hiện lại.")
            return False

        if current_time <= self.deadline:
            logger.info(
                f"Thực thi hợp đồng: {self.amount} ETH chuyển từ {self.sender[:10]}... sang {self.receiver[:10]}...")
            # In a real system, this would involve creating a transaction
            # and adding it to the blockchain's pending transactions.
            self.executed = True
            return True
        else:
            logger.warning(f"Thực thi hợp đồng: Quá hạn! {self.amount} ETH hoàn lại cho {self.sender[:10]}...")
            # Similarly, create a refund transaction
            self.executed = True
            return True

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "deadline": self.deadline,
            "executed": self.executed
        }

    @staticmethod
    def from_dict(data):
        contract = SmartContract(
            sender=data["sender"],
            receiver=data["receiver"],
            amount=data["amount"],
            deadline=data["deadline"]
        )
        contract.executed = data["executed"]
        logger.debug(f"Smart Contract được tải từ dict. Executed: {contract.executed}")
        return contract


def print_wallet_info(name, wallet):
    # This function uses print, you could switch it to logger.info if preferred.
    print(f"\n===== Ví của {name} =====")
    print(f"Private Key : {wallet.get_private_key()[:10]}...")
    print(f"Public Key (Address): {wallet.get_public_key()[:10]}...")
    print(f"RIPEMD160 Address: {wallet.get_address()[:10]}...")
    print("==========================")
    logger.info(f"Thông tin ví {name}: Địa chỉ RIPEMD160: {wallet.get_address()[:10]}...")