from flask import Flask, render_template, request, redirect, url_for
from flask_pymongo import PyMongo
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

app.config["MONGO_URI"] = "mongodb://localhost:27017/quizApp"
db = PyMongo(app).db

scheduler = BackgroundScheduler()
def startQuiz(id):
    db.quiz.update_one({"_id":id}, {"$set":{"status":"active"}})
def endQuiz(id):
    db.quiz.update_one({"_id":id}, {"$set":{"status":"finished"}})
def resCalcQuiz(id):
    db.quiz.update_one({"_id":id}, {"$set":{"resStatus":"active"}})

crTime = datetime.now()

currInActQ = db.quiz.count_documents({"startTime":{"$gt":crTime}})
if currInActQ > 0:
    currInActQ = db.quiz.find({"startTime":{"$gt":crTime}})
    for q in currInActQ:
        scheduler.add_job(startQuiz, "date", run_date = q["startTime"], args = [q["_id"]])
        scheduler.add_job(endQuiz, "date", run_date = q["endTime"], args = [q["_id"]])
        scheduler.add_job(resCalcQuiz, "date", run_date = (q["endTime"]+timedelta(minutes=5)), args = [q["_id"]])

currActQ = db.quiz.count_documents({"startTime":{"$lte":crTime}, "endTime":{"$gt":crTime}})
if currActQ > 0:
    currActQ = db.quiz.find({"startTime":{"$lte":crTime}, "endTime":{"$gt":crTime}})
    for q in currActQ:
        scheduler.add_job(endQuiz, "date", run_date = q["endTime"], args = [q["_id"]])
        scheduler.add_job(resCalcQuiz, "date", run_date = (q["endTime"]+timedelta(minutes=5)), args = [q["_id"]])
    db.quiz.update_many({"startTime":{"$lte":crTime}, "endTime":{"$gt":crTime}}, {"$set":{"status":"active"}})

currFinQ = db.quiz.count_documents({"endTime":{"$lte":crTime}})
if currFinQ > 0:
    currFinQ = db.quiz.find({"endTime":{"$lte":crTime}})
    for q in currFinQ:
        if q["endTime"] <= (crTime - timedelta(minutes=5)):
            db.quiz.update_one({"_id": q["_id"]}, {"$set":{"resStatus":"active"}})
        else:
            scheduler.add_job(resCalcQuiz, "date", run_date = (q["endTime"]+timedelta(minutes=5)), args = [q["_id"]])
    db.quiz.update_many({"endTime":{"$lte":crTime}}, {"$set":{"status":"finished"}})

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/quizzes", methods=["GET", "POST"])
def quizzes():
    if request.method == "POST":
        current = datetime.now()
        startTime = datetime.strptime(request.form["startTime"], "%Y-%m-%dT%H:%M")
        endTime = datetime.strptime(request.form["endTime"], "%Y-%m-%dT%H:%M")
        if current > startTime:
            return redirect(url_for('errmsg', errm="Start Time less than current time. Choose Again"))

        if endTime < startTime:
            return redirect(url_for('errmsg', errm="End Time less than Start time. Choose Again"))
       
        quizObj = {
            "_id": db.quiz.count_documents({}),
            "topic": request.form["topic"],
            "question": request.form["question"],
            "option-1": request.form["option-1"],
            "option-2": request.form["option-2"],
            "option-3": request.form["option-3"],
            "option-4": request.form["option-4"],
            "answer": request.form["answer"],
            "startTime": startTime,
            "endTime": endTime,
            "status": "inactive",
            "resStatus": "inactive"
        }

        scheduler.add_job(startQuiz, "date", run_date = quizObj["startTime"], args = [quizObj["_id"]])
        scheduler.add_job(endQuiz, "date", run_date = quizObj["endTime"], args = [quizObj["_id"]])
        scheduler.add_job(resCalcQuiz, "date", run_date = (quizObj["endTime"]+timedelta(minutes=5)), args = [quizObj["_id"]])

        db.quiz.insert_one(quizObj)
        return redirect(url_for('index'))
    return render_template("quizzes.html")

@app.route("/error")
def errmsg():
    errm = request.args.get('errm', None)
    return render_template("error.html", err=errm)

@app.route("/quizzes/active")
def activeQuiz():
    return render_template("activeQuiz.html", activeQList = db.quiz.find({"status":"active"}))

@app.route("/quizzes/all")
def allQuiz():
    return render_template("allQuiz.html", activeQList = db.quiz.find({"status":"active"}), inactiveQList = db.quiz.find({"status":"inactive"}), finishQList = db.quiz.find({"status":"finished"}))

@app.route("/showQuiz/<int:id>")
def showQuiz(id):
    data = db.quiz.find_one({"_id":id})
    return render_template("showQuiz.html", quizData = data)

@app.route("/quizzes/<int:id>/result")
def resultRead(id):
    data = db.quiz.find_one({"_id":id})
    if data["resStatus"] == "inactive":
        return redirect(url_for('errmsg', errm="Result is being prepared. Please Wait for 5 minutes"))
    else:
        return render_template("resultRead.html", quizData = data)

if __name__== '__main__':
    scheduler.start()
    print(scheduler.get_jobs())
    app.run(debug=True)