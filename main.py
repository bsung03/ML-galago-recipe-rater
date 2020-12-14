import sys, csv, json, math, numpy, multiprocessing , time, random
from collections import Counter 
from scipy import spatial


class Recipe:

    def __init__(self,name,id):
        self.name = name
        self.id = id
        self.ingredients = {}
        self.usersWhoRated = []
        self.clusters = {}
    
    def setCluster(self,cluster_name,val):
        self.clusters[cluster_name] = val

    def getMainCluster(self):
        Min = 2.0
        cluster = ''
        for c in self.clusters:
            if self.clusters[c] < Min:
                Min = self.clusters[c]
                cluster = c
        return cluster

    def getAverageRating(self):
        averageRate = 0.0
        for user_id in self.usersWhoRated:
            user = allUsers_train[user_id]
            averageRate = averageRate + user.getRate(self.id)
        averageRate = averageRate / float(len(self.usersWhoRated))
        return averageRate


    def changeIngredientValue(self,ing,val):
        self.ingredients[ing] = val

    def addIngredient(self,ing,val):
        self.ingredients[ing] = val
    
    def addUserRating(self,user_id):
        self.usersWhoRated.append(user_id)

class Rating:
    def __init__(self,id,rate):
        if id == '':
            print("No recipe rating id")
        elif rate == '':
            print("No recipe rate score")
        else:
            self.id = id
            self.rate = float(rate)
            if float(rate) >= 3:
                self.liked = True
            else:
                self.liked = False


class User(object):
    def __init__(self,id):
        if id == '':
            print("No User id")
        else:
            self.id = id
            self.ratings = {}
            self.rated = []
            self.averageRate = 0.0
            self.normal = True
            self.clusters = {}

    def setCluster(self,cluster_name,val):
        self.clusters[cluster_name] = val

    def getMainCluster(self):
        Max = 0.0
        cluster = ''
        for c in self.clusters:
            if self.clusters[c] > Max:
                Max = self.clusters[c]
                cluster = c
        return cluster

    def addRating(self,id,rate):
        newRating = Rating(id,rate)
        self.ratings[id] = newRating
        self.rated.append(id)

    def updateRating(self,recipe_id,val):
        newRating = Rating(recipe_id,val)
        self.ratings[recipe_id] = newRating

    def getRate(self,rec_id):
        return self.ratings[rec_id].rate

    def updateAverageRate(self):
        sum = 0.0
        for r in self.ratings:
            sum = sum + self.ratings[r].rate
        
        self.averageRate = sum / float(len(self.ratings))

    def normalize(self):
        self.normal = False
        for rating in self.ratings:
            self.ratings[rating].rate = self.ratings[rating].rate - self.averageRate
    
    def unnormalize(self):
        self.normal = True
        for rating in self.ratings:
            self.ratings[rating].rate = self.ratings[rating].rate + self.averageRate
    



class TestUser(User):
    def __init__(self,id):
        super(TestUser, self).__init__(id)
        self.missingRated = []
        self.missingRatings = {}
    
    def findmissingRated(self,allRecipes):
        for rec in allRecipes:
            if allRecipes[rec].id not in self.rated:
                self.missingRated.append(allRecipes[rec].id)
        
    def addMissingRating(self,rec_id,rate):
        self.missingRatings[rec_id] = rate
    

def parseRecipes(filePath):

    allRecipes = {}

    with open(filePath, mode ='r') as file:     
        
        # reading the CSV file 
        csvFile = csv.DictReader(file) 
    
        # displaying the contents of the CSV file 
        for lines in csvFile: 
            newRecipe = Recipe(lines['dish_name'],lines['dish_id'])
            for ing in lines:
                if ing != 'dish_id' and ing != 'dish_name':
                    newRecipe.addIngredient(ing,float(lines[ing]))
                    if ing not in allingredients:
                        allingredients.append(ing)
            allRecipes[newRecipe.id] = newRecipe
            
    file.close()
    # print("Recipes Parsed")
    return allRecipes

def parseUsers(filePath,test):

    allUsers = {}

    f = open(filePath)

    data = json.load(f)

    for u in data:

        if test == False:
            newUser = User(u)
        else:
            newUser = TestUser(u)

        for r in data[u]:

            newUser.addRating(str(r[0]),str(r[1]))
            if test == False:
                rec = allRecipes[str(r[0])]
                rec.addUserRating(newUser.id)

        newUser.updateAverageRate()
        newUser.normalize()

        allUsers[newUser.id] = newUser

    # print("Users parsed")

    return allUsers


















def cosineSim(TestUser,TrainUser,cluster):
    # print("caluculating sim score for: " + str(TestUser.id))

    # similarRatings = intersection(TestUser.rated,TrainUser.rated)
    similarRatings = set(TestUser.ratings.keys()) & set(TrainUser.ratings.keys())

    if len(similarRatings) == 0:
        return 0.0

    testData = []
    trainData = []

    for rating_id in similarRatings:
        r1 = TestUser.ratings[rating_id].rate
        r2 = TrainUser.ratings[rating_id].rate
        testData.append(r1)
        trainData.append(r2)

    result = 1 - spatial.distance.cosine(testData,trainData)

    if cluster == False:
        matchedRatio = float(len(similarRatings)) / float(len(TestUser.rated))
    else:
        matchedRatio = 1.0

    score = result * matchedRatio

    return score


def predict(rec_id, predict_user_scores, test_user):

    upper = 0.0
    lower = 0.0

    ave = test_user.averageRate

    for u in predict_user_scores:
        train_user = allUsers_train[str(u)]

        #unweight sim score
        similarRatings = set(test_user.ratings.keys()) & set(train_user.ratings.keys())
        matchedRatio = float(len(similarRatings)) / float(len(test_user.rated))

        train_user_sim_score = abs(predict_user_scores[u] / matchedRatio)
        # train_user_sim_score = predict_user_scores[u]

        # print(str(train_user_sim_score) + " vs " + str(predict_user_scores[u]))

        train_user_rating = train_user.ratings[str(rec_id)].rate

        upper = upper + float(train_user_rating) * float(train_user_sim_score)
        lower = lower + abs(float(train_user_sim_score))
    score = ave + (upper / lower)

    return score

def predict_ratings(test_user,q):

    # print("Prediction for user: " + str(test_user.id))
    
    for missingRate_id in test_user.missingRated:

        usersWhoRatedRecipe = allRecipes[missingRate_id].usersWhoRated

        simScores = {}

        for trainUser_id in usersWhoRatedRecipe:
            simScore = cosineSim(allUsers_test[test_user.id],allUsers_train[trainUser_id],False)
            simScores[trainUser_id] = simScore

        finalScores = {}
        c = 0
        for k, v in sorted(simScores.items(), key=lambda item: item[1]):
            c = c + 1
            if c > top:
                break
            if v == 0.0:
                continue
            finalScores[k] = v
        
        if len(finalScores) == 0:
            # print("could not predict score")
            continue

        s = predict(missingRate_id, finalScores, test_user)

        test_user.addMissingRating(missingRate_id,s)
        # print("Predicted: " + str(s) + " for TestUser: " + str(test_user.id) + " Recipe: " + str(missingRate_id) )
    
    findMAE(test_user,q)





def memoryCollabFilterPart2(q):
    if testType == "multi":
        procs = []
        for test_user in allUsers_test:
            u = allUsers_test[test_user]
            if calcMAE is True:
                if test_user in ground_truth:

                    # # multiprocessing
                    p = multiprocessing.Process(target=predict_ratings, args=(u,q))
                    procs.append(p)

                    p.start()

                    # predict_ratings(allUsers_test[test_user])
            else:
                print("NEXT TEXT USER")
                predict_ratings(allUsers_test[test_user],q)

        c = 0
        for proc in procs:
            c = c + 1
            proc.join()

        printQ(c,q)

    elif testType == "single":
        for test_user in allUsers_test:
            u = allUsers_test[test_user]
            if calcMAE is True:
                if test_user in ground_truth:
                    predict_ratings(allUsers_test[test_user],q)
            else:
                print("NEXT TEXT USER")
                predict_ratings(allUsers_test[test_user],q)

    


    
    



    























def pickseeds(nseeds,clss):
    seeds = []
    for i in range(nseeds):
        if clss == "recipe":
            ID = str(i)
            Name = "cluster_" + str(i)
            cluster = Recipe(Name,ID)

            for ing in allingredients:
                val = random.random()
                cluster.addIngredient(ing,val)

            # add = True
            # for s in seeds:
            #     if s.ingredients.values() == cluster.ingredients.values():
            #         nseeds = nseeds + 1
            #         add = False
            #         break
            # if add == True:
        elif clss == "user":
            Name = "cluster_" + str(i)
            cluster = User(Name)

            for rec_id in allRecipes:
                val = float(random.randint(2,4))
                cluster.addRating(rec_id,val)



        seeds.append(cluster)
                
        

    return seeds

def findDist(cluster, recipe):
    lst1 = []
    lst2 = []
    cings = cluster.ingredients
    rings = recipe.ingredients

    for i in allingredients:
        lst1.append(float(cings[i]))
        lst2.append(float(rings[i]))

    result = 1 - spatial.distance.cosine(lst1,lst2)

    return result

def assignClusters(centroids,clss):

    if clss == "recipe":
        for rec_id in allRecipes:
            recipe = allRecipes[rec_id]

            for cent in centroids:
                val = findDist(cent,recipe)
                val = 1 - val
                recipe.setCluster(cent.name,val)
    elif clss == "user":
        for user_id in allUsers_train:
            user = allUsers_train[user_id]

            for cent in centroids:
                val = cosineSim(user,cent,True)
                if val > 1:
                    print("this is where it is fucking up")
                user.setCluster(cent.id,val)

    pass

def pickCenteroids(oldCenteroids,clss):

    centroids = []
    for oldcent in oldCenteroids:
        if clss == "recipe":
            updated_cluster = Recipe(oldcent.name,oldcent.id)
            cluster_name = oldcent.name

            ings = {}
            for j in allingredients:
                ings[j] = 0.0

            c = 0
            for rec_id in allRecipes:
                recipe = allRecipes[rec_id]
                if recipe.getMainCluster() == cluster_name:
                    c = c + 1
                    for i in recipe.ingredients:
                        ings[i] = ings[i] + recipe.ingredients[i]

            for x in ings:
                ings[x] = ings[x] / float(c)

            updated_cluster.ingredients = ings

            centroids.append(updated_cluster)
        elif clss == "user":
            updated_cluster = User(oldcent.id)
            cluster_name = oldcent.id

            c = {}
            for rec_id in allRecipes:
                # print(rec_id)
                c[rec_id] = 0
                updated_cluster.addRating(rec_id,"0")
            
        
            for user_id in allUsers_train:

                user = allUsers_train[user_id]
                if user.getMainCluster() == cluster_name:
                    for i in user.ratings:
                        c[i] = c[i] + 1
                        ur = user.getRate(i)
                        crr = updated_cluster.getRate(i)

                        p = crr + ur
                        updated_cluster.updateRating(i,p)

            for i in allRecipes:
                x = c[i]
                if x == 0:
                    x = 1
                val = updated_cluster.getRate(i) / x
                updated_cluster.updateRating(i,val)

            centroids.append(updated_cluster)
                    


    return centroids


def cluster(rk,rnseeds,uk,unseeds,q):

    centroidsRec = pickseeds(rnseeds,"recipe")
    # for c in centroids:
    #     print(c.name)
    for i in range(rk):
        assignClusters(centroidsRec,"recipe")
        centroidsRec = pickCenteroids(centroidsRec,"recipe")

    # print("Recipes Clustered")
    
    # for c in centroids:
    #     name = c.name
    #     x = 0
    #     for r in allRecipes:
    #         if allRecipes[r].getMainCluster() == name:
    #             x = x + 1
    #     print(name)
    #     print(x)


    centroidsUser = pickseeds(unseeds,"user")
    for i in range(uk):
        assignClusters(centroidsUser,"user")
        centroidsUser = pickCenteroids(centroidsUser,"user")

    # print("Users Clustered")

    # t = 0
    # res = []
    # for c in centroidsUser:
    #     name = c.id
    #     x = 0
    #     for r in allUsers_train:
    #         if allUsers_train[r].getMainCluster() == name:
    #             x = x + 1
    #             t = t + 1
    #     res.append(float(x) / 500.0)

    # res.sort()
    # print(res)
    # print("total")
    # print(t)

    # for u in allUsers_test:
    #     user = allUsers_test[u]
    #     if user.id == :
    #         clusterPredict(user,centroidsUser,centroidsRec)
    if testType == "multi":

        procs = []


        for test_user in allUsers_test:
            u = allUsers_test[test_user]
            if calcMAE is True:
                if test_user in ground_truth:
                    p = multiprocessing.Process(target=clusterPredict, args=(u,centroidsUser,centroidsRec,q))
                    procs.append(p)

                    p.start()

                    # predict_ratings(allUsers_test[test_user])
            else:
                print("NEXT TEXT USER")
                clusterPredict(u,centroidsUser,centroidsRec,q)

        c = 0
        for proc in procs:
            c = c + 1
            proc.join()

        printQ(c,q)

                

    elif testType == "single":
        for test_user in allUsers_test:
            u = allUsers_test[test_user]
            if calcMAE is True:
                if test_user in ground_truth:
                    clusterPredict(u,centroidsUser,centroidsRec,q)
            else:
                print("NEXT TEXT USER")
                clusterPredict(u,centroidsUser,centroidsRec,q)

    pass







def clusterPredict(user,User_centroids, Recipe_centroids,q):

    Similar_User_Centroid = ''

    for cent in User_centroids:
        if Similar_User_Centroid == '':
            Similar_User_Centroid = cent
        if cosineSim(user,cent,True) > cosineSim(user,Similar_User_Centroid,True):
            Similar_User_Centroid = cent

    if Similar_User_Centroid == '':
        print("could not find similar user centroid")
        return


    RecipePreditions = {}
    for cent in Recipe_centroids:
        x = 0
        s = 0.0
        for rec in allRecipes:
            if cent.name == allRecipes[rec].getMainCluster():
                s = s + allRecipes[rec].getAverageRating()
                x = x + 1

        s = float(s) / float(x)
        RecipePreditions[cent] = s





    finalPredictions = {}
    for rec_id in user.missingRated:

        aveRate = 0.0
        x = 0
        for u in allUsers_train:
            train_user = allUsers_train[u]
            if train_user.getMainCluster() == Similar_User_Centroid.id:
                try:
                    aveRate = aveRate + train_user.getRate(rec_id)
                    x = x + 1
                except KeyError:
                    continue


        try:
            aveRate = aveRate / float(x)
        except ZeroDivisionError:
            continue
        # print(aveRate)
        try:
            aveRec = 0.0
            recipe = allRecipes[rec_id]
            for cent in RecipePreditions:
                if cent.name == recipe.getMainCluster():
                    aveRec = RecipePreditions[cent]

            prediction = aveRate + aveRec
            prediction = prediction / 2.0

            finalPredictions[rec_id] = prediction
        except KeyError:
            continue

    user.missingRatings = finalPredictions
    if calcMAE == True:
        findMAE(user,q)
    return finalPredictions


def memoryCollabFilterPart1(q):

    rk = 2
    rnseeds = 10
    uk = 5
    unseeds = 10

    for u in allUsers_train:
        if allUsers_train[u].normal == False:
            allUsers_train[u].unnormalize()


    cluster(rk,rnseeds,uk,unseeds,q)


    for u in allUsers_train:
        if allUsers_train[u].normal == True:
            allUsers_train[u].normalize()
    # for r in allRecipes:
        # if allRecipes[r].getMainCluster() == '':
        #     print(allRecipes[r].name)
        # print(allRecipes[r].getMainCluster())



    pass
            






































def printQ(c,q):

    mae = 0.0
    rec10 = 0.0
    rec20 = 0.0
    pre10 = 0.0
    pre20 = 0.0
    for i in range(c):
        pr = q.get()
        mae = mae + float(pr[0])
        rec10 = rec10 + float(pr[1])
        rec20 = rec20 + float(pr[2])
        pre10 = pre10 + float(pr[3])
        pre20 = pre20 + float(pr[4])
        # for s in pr:
        #     print(s)

    mae = mae / float(c)
    rec10 = rec10 / float(c)
    rec20 = rec20 / float(c)
    pre10 = pre10 / float(c)
    pre20 = pre20 / float(c)

    print("Task 1 MAE: " + str(mae))
    print("Task 2 Precision@10: " + str(pre10))
    print("Task 2 Precision@20: " + str(pre20))
    print("Task 2 Recall@10: " + str(rec10))
    print("Task 2 Recall@20: " + str(rec20))































































def findMAE(user,q):
    truth_user = ground_truth[user.id]
    if truth_user.normal == False:
        truth_user.unnormalize()
    sum = 0.0
    count = 0.0
    for rating_id in user.missingRatings:
        if rating_id in truth_user.rated:
            count = count + 1.0
            x = truth_user.ratings[rating_id].rate
            y = user.missingRatings[rating_id]
            diff = abs(x - y)
            sum = sum + diff
    
    MAE = sum / count
    maestr = MAE # str("Test User: " + str(user.id) + " MAE: " + str(MAE) + " for " + str(count) + " matches")
    recall10 = getRecall(user,10) # str("Recall@10: " + str(getRecall(user,10)))
    recall20 = getRecall(user,20) #str("Recall@20: " + str(getRecall(user,20)))
    precision10 = getPrecision(user,10) # str("Precision@10: " + str(getPrecision(user,10)))
    precision20 = getPrecision(user,20)#str("Precision@20: " + str(getPrecision(user,20)))
    pr = [maestr,recall10,recall20,precision10,precision20]
    q.put(pr)
    pass


def recommend(user,truth):
    recommended = {}

    if user.normal == False:
        user.unnormalize()

    if truth == False:
        for rec in user.missingRatings:
            rate = user.missingRatings[rec]
            if  rate >= 3.0:
                recommended[rec] = rate
    elif truth == True:
        for rec in user.ratings:
            rate = user.getRate(rec)
            if rate >= 3.0:
                recommended[rec] = rate
    
    return recommended


def getRecall(user,x):

    truth_user = ground_truth[user.id]
    if truth_user.normal == False:
        truth_user.unnormalize()
    
    tr = recommend(truth_user,True)
    ur = recommend(user,False)

    sort_orders = sorted(tr.items(), key=lambda x: x[1], reverse=True)

    tr2 = {}
    j = 0
    for i in sort_orders:
        j = j + 1
        tr2[i[0]] = i[1]
        if j > x:
            break

    sort_orders = sorted(ur.items(), key=lambda x: x[1], reverse=True)

    ur2 = {}
    j = 0
    for i in sort_orders:
        j = j + 1
        ur2[i[0]] = i[1]
        if j > x:
            break

    relret = 0.0

    for i in tr2:
        for j in ur2:
            if i == j:
                relret = relret + 1.0
    rel = float(len(tr))
    recall = relret / rel
    
    return recall

def getPrecision(user,x):

    truth_user = ground_truth[user.id]
    if truth_user.normal == False:
        truth_user.unnormalize()
    
    tr = recommend(truth_user,True)
    ur = recommend(user,False)

    sort_orders = sorted(tr.items(), key=lambda x: x[1], reverse=True)

    tr2 = {}
    j = 0
    for i in sort_orders:
        j = j + 1
        tr2[i[0]] = i[1]
        if j > x:
            break

    sort_orders = sorted(ur.items(), key=lambda x: x[1], reverse=True)

    ur2 = {}
    j = 0
    for i in sort_orders:
        j = j + 1
        ur2[i[0]] = i[1]
        if j > x:
            break

    relret = 0.0

    for i in tr2:
        for j in ur2:
            if i == j:
                relret = relret + 1.0

    ret = float(x)

    precision = relret / ret

    return precision




def main():
    if len(sys.argv) >= 3:

        dishesFilePath = sys.argv[1]
        usersTrainFilePath = sys.argv[2]
        testfilepath = sys.argv[3]

        part = sys.argv[5]
        global top 
        top = 30

        global testType
        testType = sys.argv[4]

        global calcMAE
        calcMAE = True

        global allingredients
        allingredients = []

        global allRecipes
        allRecipes = parseRecipes(dishesFilePath)


        global allUsers_train 
        allUsers_train = parseUsers(usersTrainFilePath,False)
        global allUsers_test 
        allUsers_test= parseUsers(usersTrainFilePath,True)

        global ground_truth
        ground_truth = parseUsers(testfilepath,True)

        for user in allUsers_test:
            allUsers_test[user].findmissingRated(allRecipes)

        q = multiprocessing.Queue()

        if str(part) == "1":
            # print("Part 1")
            memoryCollabFilterPart2(q)
        elif str(part) == "2":
            # print("Part 2")
            memoryCollabFilterPart1(q)

        # example()


    else:
        print("Not enough args")

if __name__ == "__main__":
   main()
