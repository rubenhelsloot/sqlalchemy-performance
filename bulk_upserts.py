"""
This series of tests illustrates different ways to UPSERT
or INSERT ON CONFLICT UPDATE a large number of rows in bulk.
"""
from sqlalchemy import Column
from sqlalchemy import create_engine
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from profiler import Profiler


Base = declarative_base()
engine = None


class Customer(Base):
  __tablename__ = "customer"
  id = Column(Integer, primary_key=True)
  name = Column(String(255))
  description = Column(String(255))


Profiler.init("bulk_upserts", num=100000)


@Profiler.setup
def setup_database(dburl, echo, num):
  global engine
  engine = create_engine(dburl, echo=echo)
  Base.metadata.drop_all(engine)
  Base.metadata.create_all(engine)

  s = Session(engine)
  for chunk in range(0, num, 10000):
    # Insert half of the customers we want to merge
    s.bulk_insert_mappings(
      Customer,
      [
        {
          "id": i,
          "name": "customer name %d" % i,
          "description": "customer description %d" % i,
        }
        for i in range(chunk, chunk + 10000, 2)
      ],
    )
  s.commit()


@Profiler.profile
def test_customer_individual_orm_select(n):
  """
  UPSERT statements via individual checks on whether objects exist
  and add new objects individually
  """
  session = Session(bind=engine)
  for i in range(0, n):
    customer = session.query(Customer).get(i)
    if customer:
      customer.description += "updated"
    else:
      session.add(Customer(
          id=i,
          name=f"customer name {i}",
          description=f"customer description {i} new"
      ))
    session.flush()
  session.commit()

@Profiler.profile
def test_customer_batched_orm_select(n):
  """
  UPSERT statements via batched checks on whether objects exist
  and add new objects individually
  """
  session = Session(bind=engine)
  for chunk in range(0, n, 1000):
    customers = {
        c.id: c for c in
        session.query(Customer)\
            .filter(Customer.id.between(chunk, chunk + 1000))
    }
    for i in range(chunk, chunk + 1000):
      if i in customers:
        customers[i].description += "updated"
      else:
        session.add(Customer(
            id=i,
            name=f"customer name {i}",
            description=f"customer description {i} new"
        ))
    session.flush()
  session.commit()

@Profiler.profile
def test_customer_batched_orm_select_add_all(n):
  """
  UPSERT statements via batched checks on whether objects exist
  and add new objects in bulk
  """
  session = Session(bind=engine)
  for chunk in range(0, n, 1000):
    customers = {
        c.id: c for c in
        session.query(Customer)\
            .filter(Customer.id.between(chunk, chunk + 1000))
    }
    to_add = []
    for i in range(chunk, chunk + 1000):
      if i in customers:
        customers[i].description += "updated"
      else:
        to_add.append({
            "id": i,
            "name": "customer name %d" % i,
            "description": "customer description %d new" % i,
        })
    if to_add:
      session.bulk_insert_mappings(
        Customer,
        to_add
      )
      to_add = []
    session.flush()
  session.commit()

@Profiler.profile
def test_customer_batched_orm_select_add_all_no_flush(n):
  """
  UPSERT statements via batched checks on whether objects exist
  and add new objects in bulk - without flushing
  """
  session = Session(bind=engine)
  for chunk in range(0, n, 1000):
    customers = {
        c.id: c for c in
        session.query(Customer)\
            .filter(Customer.id.between(chunk, chunk + 1000))
    }
    to_add = []
    for i in range(chunk, chunk + 1000):
      if i in customers:
        customers[i].description += "updated"
      else:
        to_add.append({
            "id": i,
            "name": "customer name %d" % i,
            "description": "customer description %d new" % i,
        })
    if to_add:
      session.bulk_insert_mappings(
        Customer,
        to_add
      )
      to_add = []
  session.commit()

@Profiler.profile
def test_customer_batched_orm_merge_result(n):
  "UPSERT statements using batched merge_results"
  session = Session(bind=engine)
  for chunk in range(0, n, 1000):
    customers = session.query(Customer)\
        .filter(Customer.id.between(chunk, chunk + 1000))
    customers.merge_result(
        Customer(
            id=i,
            name=f"customer name {i}",
            description=f"customer description {i} new"
        ) for i in range(chunk, chunk + 1000)
    )
    session.flush()
  session.commit()
