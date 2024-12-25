import math
import requests
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import logging

# Настройка логирования
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Глобальное определение приоритетов (больше число = выше приоритет)
PRIORITY_RANKING = {
    "critical": 5,
    "urgent": 4,
    "high": 3,
    "medium": 2,
    "low": 1
}


def haversine_distance(coord1, coord2):
    """
    Вычисляет расстояние между двумя точками на Земле по формуле Хаверсайна.

    Args:
        coord1 (tuple): Координаты первой точки (широта, долгота).
        coord2 (tuple): Координаты второй точки (широта, долгота).

    Returns:
        float: Расстояние в километрах.
    """
    R = 6371  # Радиус Земли в километрах
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def handle_refusal(route, deliveries, warehouses, warehouse_stock):
    """
    Обрабатывает доставки, которые были отказаны (не смогли быть выполнены), возвращая товары на ближайший склад.

    Args:
        route (list): Текущий маршрут с шагами.
        deliveries (list): Список объектов DeliveryAddress.
        warehouses (list): Список словарей складов.
        warehouse_stock (dict): Текущий уровень запасов на каждом складе.
    """
    # Создаем отображение от ID доставки к объекту DeliveryAddress
    delivery_map = {d.id: d for d in deliveries}

    for step in route:
        if step["type"] == "delivery" and step.get("refused", False):
            delivery_id = step["id"]
            if delivery_id not in delivery_map:
                logger.warning(f"Доставка с ID {delivery_id} не найдена в delivery_map.")
                continue

            refusal_guid = f"REFUSED_{delivery_id}"
            step["refused_guid"] = refusal_guid
            logger.info(f"Отказ на доставку {delivery_id}. GUID: {refusal_guid}")

            delivery = delivery_map[delivery_id]
            refused_items = delivery.items
            delivery_coord = delivery.coord

            # Поиск ближайшего склада с достаточной вместимостью
            best_wh = None
            best_dist = float("inf")
            total_demand = sum(it.count for it in refused_items)

            for wh in warehouses:
                dist = haversine_distance(delivery_coord, wh["coord"])
                if wh["usage"] + total_demand <= wh["capacity"]:
                    if dist < best_dist:
                        best_dist = dist
                        best_wh = wh["id"]

            if not best_wh:
                logger.error(f"Все склады переполнены! Не можем вернуть доставку {delivery_id}")
                continue

            # Добавление товаров обратно на склад и обновление использования
            wh_id = best_wh
            for item in refused_items:
                guid = item.guid
                cnt = item.count
                warehouse_stock[wh_id][guid] = warehouse_stock[wh_id].get(guid, 0) + cnt

            # Обновление использования склада
            for wh in warehouses:
                if wh["id"] == wh_id:
                    wh["usage"] += total_demand
                    break

            # Отметка доставки как отказанной в маршруте
            step["id"] = None

            # Добавление шага возврата на склад в маршрут
            route.append({
                "node_index": -1,
                "type": "warehouse_return",
                "id": wh_id,
                "arrival_time": None,
                "capacity_used": None,
                "comment": f"Возврат {delivery_id}",
                "refused_guid": refusal_guid
            })
            logger.info(f"Товары доставки {delivery_id} возвращены на склад {wh_id}.\n")

    # Логирование текущих запасов на складах
    logger.info("[handle_refusal] Текущие остатки по складам:")
    for wh in warehouses:
        wh_id = wh["id"]
        logger.info(f"  Склад {wh_id} usage={wh['usage']}/{wh['capacity']}, stock={warehouse_stock[wh_id]}")
    logger.info("-- Конец обработки отказов --\n")


def update_warehouse_after_delivery(served_orders, warehouse_stock, warehouses):
    """
    Обновляет запасы и использование на складе после выполнения доставок.

    Args:
        served_orders (list): Список выполненных доставок (DeliveryAddress).
        warehouse_stock (dict): Текущий уровень запасов на каждом складе.
        warehouses (list): Список словарей складов.
    """
    # Создаем отображение от ID склада к словарю склада
    warehouse_dict = {w["id"]: w for w in warehouses}

    for order in served_orders:
        wh_id = order.origin_warehouse
        if not wh_id or wh_id not in warehouse_dict:
            logger.warning(f"У заказа {order.id} неверный origin_warehouse: {wh_id}")
            continue

        # Расчет общего спроса для заказа
        total_demand = sum(it.count for it in order.items)

        # Уменьшение использования склада
        warehouse_dict[wh_id]["usage"] -= total_demand
        if warehouse_dict[wh_id]["usage"] < 0:
            logger.error(f"Использование склада {wh_id} ушло в минус!")

        # Уменьшение запасов по каждому товару
        for it in order.items:
            guid = it.guid
            cnt = it.count
            current_stock = warehouse_stock[wh_id].get(guid, 0)
            if current_stock < cnt:
                logger.error(
                    f"Недостаточно товара {guid} на складе {wh_id}. Требуется: {cnt}, доступно: {current_stock}")
            else:
                warehouse_stock[wh_id][guid] -= cnt


def build_subproblem(remaining_deliveries, depot_coord, warehouses):
    """
    Строит данные подзадачи для решателя VRP.

    Args:
        remaining_deliveries (list): Список объектов DeliveryAddress.
        depot_coord (list): Координаты депо [широта, долгота].
        warehouses (list): Список словарей складов.

    Returns:
        dict: Данные подзадачи, включая точки, временные окна, время обслуживания и спрос.
    """
    # 1. Агрегирование всех точек: депо, склады, доставки
    sub_points = [depot_coord]
    sub_wh_list = []
    for w in warehouses:
        sub_points.append(w["coord"])
        sub_wh_list.append(w)

    sub_del_list = []
    for d in remaining_deliveries:
        sub_points.append(d.coord)
        sub_del_list.append(d)

    # 2. Запрос матриц расстояний и продолжительности из OSRM
    coords_str = ";".join([f"{lon},{lat}" for lat, lon in sub_points])
    base_url = "http://router.project-osrm.org"
    url = f"{base_url}/table/v1/driving/{coords_str}?annotations=distance,duration"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.exception(f"Запрос к OSRM не удался: {e}")
        raise

    if "distances" not in data or "durations" not in data:
        logger.error("Недопустимая подматрица OSRM")
        raise Exception("Недопустимая подматрица OSRM")

    sub_distance_matrix = data["distances"]
    sub_duration_matrix = data["durations"]
    sub_time_matrix = [
        [math.ceil(x / 60) for x in row] for row in sub_duration_matrix
    ]

    # 3. Определение временных окон, времени обслуживания и спроса для каждой точки
    sub_time_windows = []
    sub_service_times = []
    sub_demands = []
    total_nodes = len(sub_points)

    # Узел 0: Депо
    sub_time_windows.append((0, 1440))  # Депо имеет окно на весь день
    sub_service_times.append(0)  # Время обслуживания в депо = 0
    sub_demands.append(0)  # Спрос в депо = 0

    # Узлы 1..k: Склады (точки для пополнения)
    for w in sub_wh_list:
        sub_time_windows.append((0, 1440))  # Склады имеют окно на весь день
        sub_service_times.append(5)  # Время обслуживания для пополнения = 5 минут
        sub_demands.append(0)  # Спрос для пополнения = 0

    # Узлы k+1..k+m: Доставки
    for d in sub_del_list:
        tw = getattr(d, "time_window", (0, 1440))  # Временное окно доставки
        service_time = getattr(d, "service_time", 10)  # Время обслуживания доставки
        demand = d.demand  # Спрос доставки
        sub_time_windows.append(tw)
        sub_service_times.append(service_time)
        sub_demands.append(demand)

    return {
        "sub_points": sub_points,
        "wh_list": sub_wh_list,
        "del_list": sub_del_list,
        "distance_matrix": sub_distance_matrix,
        "time_matrix": sub_time_matrix,
        "time_windows": sub_time_windows,
        "service_times": sub_service_times,
        "demands": sub_demands
    }


def solve_vrp_multy_warehouse(sub_data, deliveries, vehicle_capacity=20, big_penalty=100000):
    """
    Решает задачу маршрутизации с несколькими складами, временными окнами и приоритетами доставок.
    Более высокие приоритеты доставок обрабатываются раньше.

    Args:
        sub_data (dict): Данные подзадачи, подготовленные функцией build_subproblem.
        deliveries (list): Список объектов DeliveryAddress.
        vehicle_capacity (int, optional): Вместимость транспортного средства. По умолчанию 20.
        big_penalty (int, optional): Штраф за пропуск доставки. По умолчанию 100000.

    Returns:
        tuple: (route_nodes, skipped_nodes)
            - route_nodes (list): Упорядоченный список индексов узлов в маршруте.
            - skipped_nodes (list): Список индексов узлов, которые были пропущены.
    """
    dist_m = sub_data["distance_matrix"]
    time_m = sub_data["time_matrix"]
    tw = sub_data["time_windows"]
    svc = sub_data["service_times"]
    dm = sub_data["demands"]

    n = len(dist_m)
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # 1 транспорт, депо на индексе 0
    routing = pywrapcp.RoutingModel(manager)

    # Колбэк для расчета времени перемещения и обслуживания между узлами
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        travel_time = time_m[from_node][to_node]
        service_time = svc[from_node]
        return travel_time + service_time

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Добавление временного измерения с временными окнами
    time_dimension = routing.AddDimension(
        transit_callback_index,
        0,  # Нет допуска времени
        1440,  # Максимальное время маршрута (24 часа)
        False,  # Не фиксировать начало маршрута
        "Time"
    )
    time_dim = routing.GetDimensionOrDie("Time")

    # Установка временных окон для каждого узла
    for i in range(n):
        start, end = tw[i]
        index = manager.NodeToIndex(i)
        time_dim.CumulVar(index).SetRange(start, end)

    # Добавление измерения вместимости
    def demand_callback(from_index):
        return dm[manager.IndexToNode(from_index)]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # Нет допуска
        [vehicle_capacity],  # Вместимость транспортного средства
        True,  # Начальные запасы равны нулю
        "Capacity"
    )
    capacity_dim = routing.GetDimensionOrDie("Capacity")

    # Добавление дизъюнкций с штрафами за пропуск доставок
    for node in range(1, n):
        # Определение, является ли узел доставкой (не складом)
        if node > len(sub_data["wh_list"]):
            delivery_idx = node - 1 - len(sub_data["wh_list"])
            if 0 <= delivery_idx < len(sub_data["del_list"]):
                delivery = sub_data["del_list"][delivery_idx]
                priority = delivery.priority.lower()
                penalty = PRIORITY_RANKING.get(priority, 1) * 20000  # Более высокий приоритет - больший штраф
            else:
                penalty = big_penalty
        else:
            # Присвоение штрафа за пропуск склада, чтобы предотвратить его пропуск
            penalty = big_penalty

        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # Добавление ограничений предшествования на основе приоритетов
    delivery_nodes = []
    delivery_priorities = []
    for node in range(1, n):
        if node > len(sub_data["wh_list"]):
            delivery_idx = node - 1 - len(sub_data["wh_list"])
            if 0 <= delivery_idx < len(sub_data["del_list"]):
                delivery = sub_data["del_list"][delivery_idx]
                priority = PRIORITY_RANKING.get(delivery.priority.lower(), 1)
                delivery_nodes.append(manager.NodeToIndex(node))
                delivery_priorities.append(priority)

    # Обеспечение, чтобы более высокие приоритеты были посещены раньше
    for i in range(len(delivery_nodes)):
        for j in range(len(delivery_nodes)):
            if delivery_priorities[i] > delivery_priorities[j]:
                # Обеспечить, чтобы время прибытия в узел с более высоким приоритетом <= времени прибытия в узел с более низким
                routing.solver().Add(time_dim.CumulVar(delivery_nodes[i]) <= time_dim.CumulVar(delivery_nodes[j]))

    # Настройка параметров поиска
    search_params = pywrapcp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = 10  # Ограничение времени поиска

    # Решение задачи
    sol = routing.SolveWithParameters(search_params)
    if not sol:
        logger.error("[solve_vrp_multy_warehouse] Решение не найдено!")
        return None, None

    # Извлечение маршрута и времени прибытия из решения
    route_nodes = []
    arrival_times = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        node = manager.IndexToNode(idx)
        time_var = time_dim.CumulVar(idx)
        arrival_time = sol.Value(time_var)
        route_nodes.append(node)
        arrival_times.append(arrival_time)
        idx = sol.Value(routing.NextVar(idx))
    # Добавление конечного узла
    node = manager.IndexToNode(idx)
    time_var = time_dim.CumulVar(idx)
    arrival_time = sol.Value(time_var)
    route_nodes.append(node)
    arrival_times.append(arrival_time)

    # Логирование подробной информации для отладки
    logger.info(f"Временные окна: {tw}")
    logger.info(f"Время обслуживания: {svc}")
    logger.info(f"Спрос: {dm}")
    logger.info(f"Маршрутные узлы: {route_nodes}")
    logger.info(f"Времена прибытия: {arrival_times}")

    # Определение пропущенных узлов на основе того, были ли они посещены
    skipped = []
    for node in range(1, n):
        node_index = manager.NodeToIndex(node)
        # Если следующий узел после текущего - это сам узел, значит он был пропущен
        if sol.Value(routing.NextVar(node_index)) == node_index:
            skipped.append(node)

    logger.info(f"Пропущенные узлы: {skipped}")

    return route_nodes, skipped


def build_osm_route_url(route_plan, all_points):
    """
    Строит URL для отображения маршрута на OpenStreetMap.

    Args:
        route_plan (list): Список шагов маршрута с индексами узлов.
        all_points (list): Список всех координат точек, использованных в маршруте.

    Returns:
        str: URL для отображения маршрута на OSM.
    """
    base_url = "https://yandex.ru/maps/?"
    rtext_prefix = "rtext="  # Параметр для указания маршрута
    mode = "mode=routes"  # Режим отображения маршрута (можно изменить, например, на пеший)

    coords_str_list = []

    for step in route_plan:
        idx = step.get("node_index")
        if idx is None:
            logger.warning(f"Отсутствует 'node_index' в шаге маршрута: {step}. Пропуск.")
            continue
        if idx < 0 or idx >= len(all_points):
            logger.warning(f"Неверный индекс узла {idx} в route_plan.")
            continue  # Пропуск неверных индексов
        lat, lon = all_points[idx]  # Получение координат узла
        logger.debug(f"Индекс {idx}: Координаты ({lat}, {lon})")
        coords_str_list.append(f"{lat},{lon}")

    if not coords_str_list:
        logger.error("Список координат пуст. Проверьте данные.")
        return ""

    # Объединяем координаты через '~' для параметра rtext
    rtext = rtext_prefix + "~".join(coords_str_list)
    osm_url = f"{base_url}{rtext}&{mode}"
    logger.info(f"Сгенерированный URL для Яндекс.Карт: {osm_url}")
    return osm_url

def run_optimization(data):
    """
    Основная функция для запуска оптимизации маршрута доставки.

    Args:
        data (object): Объект DeliveryRequest, содержащий депо, доставки и склады.

    Returns:
        dict: Содержит 'route_order', 'osm_url' и 'message'.
    """
    try:
        # 1. Подготовка: Извлечение доставок и складов из входных данных
        deliveries_input = data.deliveries
        logger.info(f"Получены данные: {data}")
        for delivery in data.deliveries:
            logger.info(f"Доставка ID: {delivery.id}, Координаты: {delivery.coord}, Приоритет: {delivery.priority}")

        # Обработка складов и создание копии запасов
        warehouses = []
        warehouse_stock = {}
        for w in data.warehouses:
            warehouses.append({
                "id": w.id,
                "coord": w.coord,
                "capacity": w.capacity,
                "usage": w.usage,
            })
            warehouse_stock[w.id] = w.stock.copy()

        # Построение подзадачи для решателя VRP
        sub_data = build_subproblem(deliveries_input, data.depot_coord, warehouses)

        # Решение VRP
        route_nodes, skipped_nodes = solve_vrp_multy_warehouse(sub_data, deliveries_input, data.vehicle_capacity,
                                                               big_penalty=100000)

        if route_nodes is None:
            logger.warning("Решение не найдено (все доставки пропущены)")
            return {
                "route_order": [],
                "osm_url": "",
                "message": "Решение не найдено (все доставки пропущены)"
            }

        # Обработка пропущенных узлов путем отметки доставок как отказанных
        for node in skipped_nodes:
            if node > len(warehouses):
                d_idx = node - 1 - len(warehouses)
                if 0 <= d_idx < len(deliveries_input):
                    deliveries_input[d_idx].refused = True

        served_orders = []
        total_warehouses = len(warehouses)

        # Определение выполненных доставок на основе маршрута
        for node in route_nodes:
            if node > total_warehouses:  # Это "доставка"
                d_idx = node - 1 - total_warehouses
                if 0 <= d_idx < len(deliveries_input):
                    served_orders.append(deliveries_input[d_idx])

        # Обновление запасов и использования на складах после выполнения доставок
        update_warehouse_after_delivery(served_orders, warehouse_stock, warehouses)

        # Построение плана маршрута с подробными шагами
        route_plan = []
        for node in route_nodes:
            if node == 0:
                # Депо
                route_plan.append({
                    "node_index": 0,
                    "type": "depot",
                    "id": None,
                    "refused": False
                })
            elif 1 <= node <= total_warehouses:
                # Склад
                wh = warehouses[node - 1]
                route_plan.append({
                    "node_index": node,
                    "type": "warehouse",
                    "id": wh["id"],
                    "refused": False
                })
            else:
                # Доставка
                d_idx = node - 1 - total_warehouses
                if 0 <= d_idx < len(deliveries_input):
                    d = deliveries_input[d_idx]
                    route_plan.append({
                        "node_index": node,
                        "type": "delivery",
                        "id": d.id,
                        "refused": d.refused
                    })

        # Обработка отказов путем возврата товаров на склады
        handle_refusal(route_plan, deliveries_input, warehouses, warehouse_stock)

        # Генерация URL для отображения маршрута на OpenStreetMap
        osm_url = build_osm_route_url(route_plan, sub_data["sub_points"])

        # Извлечение окончательного порядка доставок для ответа
        route_order = [
            step["id"] for step in route_plan
            if step["type"] == "delivery" and step["id"] is not None and not step.get("refused", False)
        ]

        # Проверка, были ли выполнены какие-либо доставки
        if not route_order:
            osm_url = ""
            message = "Решение не найдено (все доставки пропущены)"
        else:
            message = "OK"

        # Логирование фактического и ожидаемого порядка доставки для отладки
        logger.info(f"Фактический порядок доставки: {route_order}")
        sorted_by_priority = sorted(
            [d.id for d in deliveries_input if not d.refused],
            key=lambda x: PRIORITY_RANKING.get(next((d.priority for d in deliveries_input if d.id == x), "low").lower(),
                                               1),
            reverse=True
        )
        logger.info(f"Ожидаемый порядок доставки: {sorted_by_priority}")

        # Возврат результата оптимизации
        logger.info("Оптимизация успешно завершена.")
        return {
            "route_order": route_order,
            "osm_url": osm_url,
            "message": message
        }

    except Exception as e:
        logger.exception(f"Ошибка в run_optimization: {e}")
        raise
