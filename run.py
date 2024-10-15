from operate import ServerManager


manager = ServerManager()

if manager.is_running(8500):
    manager.stop(8500)

# manager.start(
#     dsn_or_db_path="sqlite:////Users/anindya/personal/PremSQL/premsql/dataset/spider/database/coffee_shop/coffee_shop.sqlite",
#     agent_name="simple_agent"
# )