/**
 * \file search.hpp
 *
 * Copyright 2022 DTAI Research Group - KU Leuven.
 * License: Apache License 2.0
 * Author: Laurens Devos
*/

#ifndef VERITAS_SEARCH_HPP
#define VERITAS_SEARCH_HPP

#include "domain.hpp"
#include "tree.hpp"
#include "graph.hpp"
//#include "constraints.hpp"
#include <iostream>
#include <chrono>
#include <map>
#include <memory>

#include <iomanip>

namespace veritas {

    /** \private */
    using time_point = std::chrono::time_point<std::chrono::system_clock>;
    struct BaseHeuristic; /* heuristics.hpp */

    struct Solution {
        double time; 
        FloatT eps;
        FloatT output;
        BoxRef box;
    };

    struct Snapshot {
        double time = 0.0;
        size_t num_steps = 0;
        size_t num_solutions = 0;
        size_t num_open = 0;
        FloatT eps = 0.0;
        std::tuple<FloatT, FloatT, FloatT> bounds = {-FLOATT_INF, FLOATT_INF, FLOATT_INF}; // lo, up_a, up_ara
        double avg_focal_size = 0.0;
    };

    enum class StopReason {
        NONE,
        NO_MORE_OPEN,
        NUM_SOLUTIONS_EXCEEDED,
        NUM_NEW_SOLUTIONS_EXCEEDED,
        OPTIMAL,
        UPPER_LT,
        LOWER_GT,
    };

    inline
    std::ostream&
    operator<<(std::ostream& strm, StopReason r)
    {
#define VER_STOP_REASON_CASE(name) case StopReason::name: \
        strm << #name; \
        break;

        switch (r) {
            VER_STOP_REASON_CASE(NONE)
            VER_STOP_REASON_CASE(NO_MORE_OPEN)
            VER_STOP_REASON_CASE(NUM_SOLUTIONS_EXCEEDED)
            VER_STOP_REASON_CASE(NUM_NEW_SOLUTIONS_EXCEEDED)
            VER_STOP_REASON_CASE(OPTIMAL)
            VER_STOP_REASON_CASE(UPPER_LT)
            VER_STOP_REASON_CASE(LOWER_GT)
        }

        return strm;
#undef VER_STOP_REASON_CASE
    }

    /** Iterator over leafs overlapping with a box. */
    class LeafIter {
    public:
        std::vector<Domain> flatbox;

    private:
        std::vector<NodeId> stack_;
        const Tree* tree_ = nullptr;

        void copy_to_flatbox_(BoxRef box)
        {
            std::fill(flatbox.begin(), flatbox.end(), Domain{});
            for (auto &&[feat_id, dom] : box)
                flatbox.at(feat_id) = dom;
        }

    public:

        void setup_tree(const Tree& t)
        {
            tree_ = &t;
            if (!stack_.empty())
                throw std::runtime_error("iter stack not empty");
            stack_.push_back(t.root().id());
        }

        void setup_flatbox(BoxRef box)
        {
            if (!box.is_null_box())
            {
                FeatId max_feat_id = (box.end()-1)->feat_id;
                if (flatbox.size() <= static_cast<size_t>(max_feat_id))
                {
                    //std::cout << "resizing flatbox to " << (max_feat_id+1) << std::endl;
                    flatbox.resize(max_feat_id+1);
                }
            }
            copy_to_flatbox_(box);
        }

        /* setup the iterator */
        void setup(const Tree& t, BoxRef box)
        {
            setup_tree(t);
            setup_flatbox(box);
        }

        /* find next overlapping leaf */
        NodeId next()
        {
            while (!stack_.empty())
            {
                Tree::ConstRef n = tree_->node_const(stack_.back());
                stack_.pop_back();

                if (n.is_leaf())
                    return n.id();

                const LtSplit& s = n.get_split();
                Domain d;
                if (static_cast<size_t>(s.feat_id) < flatbox.size())
                    d = flatbox[s.feat_id];

                // null box is quick indicator that node is unreachable due to
                // additional constraints
                if (d.hi >= s.split_value)
                    stack_.push_back(n.right().id());
                if (d.lo < s.split_value)
                    stack_.push_back(n.left().id());
            }
            tree_ = nullptr;
            return -1;
        }
    };


    /** See Search */
    class VSearch {
    protected:
        AddTree at_;

        VSearch(const AddTree& at)
            : at_{at.neutralize_negative_leaf_values()} {}

    public:
        static std::shared_ptr<VSearch> max_output(const AddTree& at);
        static std::shared_ptr<VSearch> min_dist_to_example(const AddTree& at,
                const std::vector<FloatT>& ex,
                FloatT output_threshold);

        /* possibly different because `neutralize_negative_leaf_values` */
        FloatT base_score() const { return at_.base_score; }

    public:
        virtual StopReason step() = 0;
        virtual StopReason steps(size_t num_steps) = 0;
        virtual StopReason step_for(double num_seconds, size_t num_steps) = 0;
        virtual size_t num_solutions() const = 0;
        virtual size_t num_open() const = 0;
        virtual void set_mem_capacity(size_t bytes) = 0;
        virtual double time_since_start() const = 0;
        virtual std::tuple<FloatT, FloatT, FloatT> current_bounds() const = 0;
        virtual const Solution& get_solution(size_t solution_index) const = 0;
        virtual FloatT get_at_output_for_box(BoxRef box) const = 0;
        virtual bool is_optimal() const = 0;
        virtual void prune_by_box(BoxRef box) = 0;

        // settings
        FloatT eps = 0.95;
        size_t max_focal_size = 1000;
        bool debug = false;
        bool auto_eps = true;

        FloatT reject_solution_when_output_less_than = -FLOATT_INF;

        // stop conditions
        size_t stop_when_num_solutions_exceeds      = 9'999'999;
        size_t stop_when_num_new_solutions_exceeds  = 9'999'999;
        bool   stop_when_optimal                    = true;
        FloatT stop_when_upper_less_than            = -FLOATT_INF;
        FloatT stop_when_lower_greater_than         = FLOATT_INF;

        // statistics
        size_t num_steps = 0;
        size_t num_rejected_solutions = 0;
        std::vector<Snapshot> snapshots;
    };




    template <typename Heuristic>
    class Search : public VSearch {
        Graph graph_;
        size_t mem_capacity_;
        time_point start_time_;

        friend BaseHeuristic;
        friend Heuristic;
        using State = typename Heuristic::State;

        std::vector<State> open_;

        struct SolStatePair {
            State state;
            Solution sol;
        };
        std::vector<SolStatePair> solutions_;

        BlockStore<DomainPair> store_;

        mutable struct {
            /** \private */ Box box;
            /** \private */ std::vector<size_t> focal;
            /** \private */ LeafIter leafiter1; // expand_
            /** \private */ LeafIter leafiter2; // heurstic computation
        } workspace_;

        /** node_box_[tree][leaf_id] given constraints */
        std::vector<std::vector<BoxRef>> node_box_;

        /** how many open states did we look at in `pop_from_focal_`? */
        size_t sum_focal_size_ = 0;

        FloatT last_eps_update_time_ = 0.0;
        FloatT avg_eps_update_time_ = 0.02;
        FloatT eps_increment_ = 0.05;

    public:
        Heuristic heuristic;

    public:
        template <typename... HeurArgs>
        Search(const AddTree& at, HeurArgs... heur_args)
            : VSearch(at)
            , graph_(at_)
            , mem_capacity_(size_t(1024)*1024*1024)
            , start_time_{std::chrono::system_clock::now()}
            , heuristic(heur_args...)
        {
            init_();
        }

        StopReason step()
        {
            ++num_steps;

            if (open_.empty())
                return StopReason::NO_MORE_OPEN;

            //State state = (num_steps%2 == 1)
            //    ? pop_from_focal_()
            //    : pop_top_();
            
            State state = pop_from_focal_();

            if (is_solution_(state))
            {
                if (heuristic.output_overestimate(state) <
                        reject_solution_when_output_less_than)
                {
                    std::cout << "rejected " << heuristic.output_overestimate(state)
                        << " < " << reject_solution_when_output_less_than
                        << " (" << heuristic.open_score(state) << ")"
                        << std::endl;
                    ++num_rejected_solutions;
                }
                else
                    push_solution_(state);
                increase_eps_();
            }
            else
            {
                expand_(state);
            }

            return StopReason::NONE;
        }

        StopReason steps(size_t num_steps)
        {
            StopReason stop_reason = StopReason::NONE;
            size_t num_sol = num_solutions();
            size_t step_count = 0;
            sum_focal_size_ = 0;

            for (; stop_reason == StopReason::NONE
                    && step_count < num_steps; ++step_count)
            {
                stop_reason = step();
                if (num_sol + stop_when_num_new_solutions_exceeds
                        <= num_solutions())
                    return StopReason::NUM_NEW_SOLUTIONS_EXCEEDED;
            }

            if (stop_reason == StopReason::NONE)
            {
                if (num_solutions() >= stop_when_num_solutions_exceeds)
                    stop_reason = StopReason::NUM_SOLUTIONS_EXCEEDED;
                auto &&[lo, hi, top] = current_bounds();
                if (stop_when_optimal && is_optimal_(lo, hi, top))
                    stop_reason = StopReason::OPTIMAL;
                else if (lo > stop_when_lower_greater_than)
                    stop_reason = StopReason::LOWER_GT;
                else if (hi < stop_when_upper_less_than)
                    stop_reason = StopReason::UPPER_LT;
            }

            push_snapshot((double)sum_focal_size_ / (double)step_count);

            maybe_decrease_eps_();

            return stop_reason;
        }

        StopReason step_for(double num_seconds, size_t num_steps)
        {
            double start = time_since_start();
            StopReason stop_reason = StopReason::NONE;

            while (stop_reason == StopReason::NONE)
            {
                stop_reason = steps(num_steps);
                double dur = time_since_start() - start;
                if (dur >= num_seconds)
                    break;
            }

            return stop_reason;
        }

        void set_mem_capacity(size_t bytes) { mem_capacity_ = bytes; }
        size_t remaining_mem_capacity() const
        { return mem_capacity_ - store_.get_mem_size(); }

        /** Seconds since the construction of the search */
        double time_since_start() const
        {
            auto now = std::chrono::system_clock::now();
            return std::chrono::duration_cast<std::chrono::microseconds>(
                    now-start_time_).count() * 1e-6;
        }

        size_t num_solutions() const { return solutions_.size(); }
        size_t num_open() const { return open_.size(); }

        /** lower, upper, top of open */
        std::tuple<FloatT, FloatT, FloatT> current_bounds() const
        {
            FloatT lo = -FLOATT_INF, up = -FLOATT_INF, top = -FLOATT_INF;
            if (open_.size() > 0)
            {
                top = heuristic.open_score(open_.front());
                up = top;
            }
            if (num_solutions() > 0)
            {
                lo = heuristic.open_score(solutions_[0].state); // best solution so far, sols are sorted
                if (open_.size() == 0 || (up < lo))
                    up = lo;
            }
            return {lo, up, top};
        }

        const Solution& get_solution(size_t solution_index) const
        { return solutions_.at(solution_index).sol; }

        const State& get_solution_state(size_t solution_index) const
        { return solutions_.at(solution_index).state; }

        FloatT get_at_output_for_box(BoxRef box) const
        {
            FloatT output = at_.base_score;
            for (size_t tree_index = 0; tree_index < at_.size(); ++tree_index)
            {
                const Tree& t = at_[tree_index];
                workspace_.leafiter2.setup(t, box);
                NodeId leaf_id = workspace_.leafiter2.next();
                if (workspace_.leafiter2.next() != -1)
                    throw std::runtime_error("no unique output for box");
                output += t[leaf_id].leaf_value();
            }
            return output;
        }

        /**
         * Is `get_solution(0)` the optimal solution?
         * \return true when certainly optimal, false otherwise (= maybe optimal)
         */
        bool is_optimal() const
        {
            auto&&[lo, hi, top] = current_bounds();
            return is_optimal_(lo, hi, top);
        }

        void push_snapshot(double avg_focal_size)
        {
            snapshots.push_back({
                time_since_start(),
                num_steps,
                num_solutions(),
                num_open(),
                eps,
                current_bounds(),
                avg_focal_size,
            });
        }

        void prune_by_box(BoxRef box)
        {
            if (open_.size() > 1)
                throw std::runtime_error("invalid state: pruning after search has started");
            graph_.prune_by_box(box, false);

            for (size_t tree_index = 0; tree_index < at_.size(); ++tree_index)
            {
                for (BoxRef& node_box : node_box_[tree_index])
                {
                    if (node_box.overlaps(box))
                    {
                        combine_boxes(node_box, box, false, workspace_.box);
                        node_box = BoxRef(store_.store(workspace_.box, remaining_mem_capacity()));
                        workspace_.box.clear();
                    }
                    else
                    {
                        node_box = BoxRef::null_box();
                    }
                }
            }
        }



    private:
        void init_()
        {
            if (auto_eps)
                eps = 0.5;

            // Generate node domains
            node_box_.resize(at_.size());
            for (size_t tree_index = 0; tree_index < at_.size(); ++tree_index)
            {
                const Tree& tree = at_[tree_index];
                node_box_[tree_index].resize(tree.num_nodes(), BoxRef::null_box());
                compute_node_box_(tree_index, tree.root_const());
            }

            // Push the first search state
            State initial_state, dummy_parent;
            heuristic.update_heuristic(initial_state, *this, dummy_parent, at_.base_score);
            push_(std::move(initial_state));
        }
        
        void compute_node_box_(size_t tree_index, Tree::ConstRef n)
        {
            if (n.is_leaf())
                return;

            const LtSplit& split = n.get_split();

            BoxRef pbox = node_box_[tree_index].at(n.id());
            workspace_.box.resize(pbox.size());

            std::copy(pbox.begin(), pbox.end(), workspace_.box.begin());
            Domain& dom = get_domain(workspace_.box, split.feat_id);

            //std::cout << "parent " << pbox << std::endl;
            //std::cout << "  - split " << split << ", " << dom << std::endl;

            auto&& [ldom, rdom] = dom.split(split.split_value);

            dom = ldom;
            BoxRef lbox { store_.store(workspace_.box, remaining_mem_capacity()) };
            node_box_[tree_index][n.left().id()] = lbox;

            dom = rdom;
            BoxRef rbox { store_.store(workspace_.box, remaining_mem_capacity()) };
            node_box_[tree_index][n.right().id()] = rbox;

            //std::cout << "  - left " << lbox << std::endl;
            //std::cout << "  - right " << rbox << std::endl;

            workspace_.box.clear();

            compute_node_box_(tree_index, n.left());
            compute_node_box_(tree_index, n.right());
        }

        bool is_solution_(const State& state)
        {
            return state.indep_set+1 == static_cast<int>(at_.size());
        }

        /** \return solution index */
        size_t push_solution_(const State& state)
        {
            solutions_.push_back({
                state,
                { // sol
                    time_since_start(),
                    eps,
                    heuristic.output_overestimate(state), // output
                    state.box,
                }
            });

            // sort solutions
            size_t i = solutions_.size()-1;
            for (; i > 0; --i)
            {
                auto& sol1 = solutions_[i-1];
                auto& sol2 = solutions_[i];
                // if a solution lower in the list (sol2) is better than a
                // solution higher in the list (sol1), then swap them
                if (heuristic.cmp_open_score(sol2.state, sol1.state))
                    std::swap(sol1, sol2);
                else return i;
            }
            return 0;
        }

        void expand_(const State& state)
        {
            /*
            int next_indep_set = state.indep_set + 1;
            Graph::IndepSet set = graph_.get_vertices(next_indep_set);
            int num_vertices = static_cast<int>(set.size());
            for (int vertex = 0; vertex < num_vertices; ++vertex)
            {
                const Graph::Vertex& v = set[vertex];
                if (v.box.overlaps(state.box))
                {
                    combine_boxes(v.box, state.box, true, workspace_.box);
                    construct_and_push_states_(state, v.output);
                }
            }
            */

            size_t next_tree = state.indep_set + 1;
            const Tree& t = at_[next_tree];
            workspace_.leafiter1.setup(t, state.box);
            NodeId leaf_id = -1;
            while ((leaf_id = workspace_.leafiter1.next()) != -1)
            {
                if (node_box_[next_tree][leaf_id].is_null_box())
                {
                    //std::cout << "skipping1 " << leaf_id << " because constraints " << next_tree << std::endl;
                    continue;
                }
                BoxRef leaf_box = node_box_[next_tree][leaf_id];
                if (leaf_box.overlaps(state.box))
                {
                    combine_boxes(leaf_box, state.box, true, workspace_.box);
                    construct_and_push_states_(state, t[leaf_id].leaf_value());
                }
                else
                {
                    std::cout << "overlaps but doesn't actually overlap??\n";
                }
            }
        }

        void construct_and_push_states_(const State& parent, FloatT leaf_value)
        {
            auto push_workspace_box_fun = [this, parent, leaf_value](Box& b){
                State new_state;
                new_state.indep_set = parent.indep_set + 1;
                new_state.box = BoxRef(store_.store(b, remaining_mem_capacity()));
                if (heuristic.update_heuristic(new_state, *this, parent, leaf_value))
                    push_(std::move(new_state));
            };

            //if (constr_prop)
            //{
            //    constr_prop->check(workspace_.box, push_workspace_box_fun);
            //    //constr_prop->print();
            //}
            //else
            //{
                push_workspace_box_fun(workspace_.box);
            //}

            workspace_.box.clear();
        }

        void push_(State&& state)
        {
            //size_t state_index = push_state_(std::move(state));
            auto cmp = [this](const State& a, const State& b) {
                return heuristic.cmp_open_score(b, a); // (!) reverse: max-heap with less-than cmp
            };
            push_to_heap_(open_, std::move(state), cmp);
            //return state_index;
        }

        State pop_top_()
        {
            auto cmp = [this](const State& a, const State& b) {
                return heuristic.cmp_open_score(b, a); // (!) reverse: max-heap with less-than cmp
            };
            return pop_from_heap_(open_, cmp);
        }

        // J. Pearl and J. H. Kim, "Studies in Semi-Admissible Heuristics," in
        // IEEE Transactions on Pattern Analysis and Machine Intelligence, vol.
        // PAMI-4, no. 4, pp. 392-399, July 1982, doi:
        // 10.1109/TPAMI.1982.4767270.
        State pop_from_focal_()
        {
            if (eps == 1.0)
                return pop_top_();
            if (max_focal_size <= 1)
                return pop_top_();

            // reverse order of a and b, heap functions require less-than comparision
            auto cmp_i = [this](size_t a, size_t b) {
                return heuristic.cmp_open_score(open_[b], open_[a]); };
            auto cmp_s = [this](const State& a, const State& b) {
                return heuristic.cmp_open_score(b, a); };

            FloatT oscore = heuristic.open_score(open_.front());
            FloatT orelax = heuristic.relax_open_score(oscore, eps);
            FloatT i_best = 0;
            size_t focal_size = 0;

            workspace_.focal.clear();
            workspace_.focal.push_back(0);
            while (!workspace_.focal.empty())
            {
                size_t i = pop_from_heap_(workspace_.focal, cmp_i);
                const State& s = open_[i];

                //FloatT foc = heuristic.focal_score(s);
                //if (foc > foc_best)
                if (heuristic.cmp_focal_score(s, open_[i_best]))
                {
                    i_best = i;
                    //foc_best = foc;
                }

                if (++focal_size >= max_focal_size)
                    break;

                //std::cout << num_steps << ": " << "ref_oscore=" << oscore << ", orelax=" << orelax
                //    <<", best=" << heuristic.open_score(open_[i_best]) << "/" << open_[i_best].indep_set << ": ";
                //heuristic.print_state(std::cout, s);
                
                FloatT oscore1 = heuristic.open_score(open_[2*i+1]);
                if (2*i+1 < open_.size() && heuristic.cmp_open_score(oscore1, orelax))
                    push_to_heap_(workspace_.focal, 2*i+1, cmp_i);

                FloatT oscore2 = heuristic.open_score(open_[2*i+2]);
                if (2*i+2 < open_.size() && heuristic.cmp_open_score(oscore2, orelax))
                    push_to_heap_(workspace_.focal, 2*i+2, cmp_i);
            }

            sum_focal_size_ += focal_size;

            //std::cout << "BEST CHOICE " << i_best << ", focal_score " << foc_best
            //    << ", f=" << heuristic.open_score(open_[i_best])
            //    << " (vs " << heuristic.open_score(open_.front()) << ")" << std::endl;
            return pop_index_heap_(open_, i_best, cmp_s);
        }

        template <typename T, typename CmpT>
        void push_to_heap_(std::vector<T>& heap, T&& s, const CmpT& cmp)
        {
            heap.push_back(std::move(s));
            std::push_heap(heap.begin(), heap.end(), cmp);
        }

        template <typename T, typename CmpT>
        T pop_from_heap_(std::vector<T>& heap, const CmpT& cmp)
        {
            std::pop_heap(heap.begin(), heap.end(), cmp);
            T s = heap.back();
            heap.pop_back();
            //if constexpr (std::is_same<T, State>::value)
            //    std::cout << "first " << heuristic.open_score(s)
            //        << ", second " << heuristic.open_score(heap.front()) << std::endl;
            return s;
        }

        /**
         * max-heap with less-than comparison, i.e.,
         * cmp(a, b) == True <=> a must be lower in the heap than b
         */
        template <typename T, typename CmpT>
        T pop_index_heap_(std::vector<T>& heap, size_t index, const CmpT& cmp)
        {
            if (index == 0)
                return pop_from_heap_(heap, cmp);

            std::swap(heap.back(), heap[index]);
            T s = heap.back();
            heap.pop_back();

            //std::cout << "BEFORE\n";
            //print_heap_(heap, 0);

            // heapify up
            for (size_t i = index; i != 0;)
            {
                size_t parent = (i-1)/2;
                if (cmp(heap[i], heap[parent])) // parent larger than i
                    break; // heap prop satisfied
                //std::cout << "heapify up " << i << " <-> " << parent << std::endl;
                std::swap(heap[i], heap[parent]);
                i = parent;
            }

            // heapify down:
            // https://courses.cs.duke.edu/spring05/cps130/lectures/littman.lectures/lect08/node16.html
            for (size_t i = index;;)
            {
                size_t left = i*2 + 1;
                size_t right = i*2 + 2;
                bool has_left = left < heap.size();
                bool has_right = right < heap.size();

                if ((!has_left || cmp(heap[left], heap[i]))
                        && (!has_right || cmp(heap[right], heap[i])))
                    break;

                size_t larger = left;
                if (has_right && cmp(heap[left], heap[right]))
                    larger = right;

                //std::cout << "heapfy down " << i << " <-> " << larger;
                //std::cout << " fscores " << heuristic.open_score(heap[i])
                //    << ", " << heuristic.open_score(heap[larger])
                //    << " (" << heuristic.open_score(heap[larger==left ? right : left]) << ")" << std::endl;

                std::swap(heap[larger], heap[i]);
                i = larger;
            }

            //std::cout << "AFTER\n";
            //print_heap_(heap, 0);

            if (debug && !std::is_heap(heap.begin(), heap.end(), cmp))
            {
                print_heap_(heap);
                auto until = std::is_heap_until(heap.begin(), heap.end(), cmp);
                std::cout << "heap until " << (until-heap.begin()) << ", "
                    << heuristic.open_score(*until) << std::endl;
                throw std::runtime_error("whoops not a heap");
            }
            return s;
        }

        bool is_optimal_(FloatT lo, FloatT hi, FloatT) const
        { return lo == hi; }


        void print_heap_(const std::vector<State>& v, size_t i=0, size_t depth=0)
        {
            if (i >= v.size())
                return;
            for (size_t j = 0 ; j < depth; ++j)
                std::cout << "  ";
            std::cout << i << ": " << heuristic.open_score(v[i]) << std::endl;

            print_heap_(v, i*2 + 1, depth+1);
            print_heap_(v, i*2 + 2, depth+1);
        }

        void increase_eps_()
        {
            if (!auto_eps) return;

            double t = time_since_start();
            double time_since_previous_update = t - last_eps_update_time_;

            // if update time is similar to last time, double eps increase
            if (time_since_previous_update*2 < avg_eps_update_time_)
                eps_increment_ *= 2.0;
            
            last_eps_update_time_ = t;
            avg_eps_update_time_ = 0.2 * avg_eps_update_time_ +
                0.8*time_since_previous_update;

            FloatT old_eps = eps;
            eps = std::min<FloatT>(1.0, eps+eps_increment_);

            if (debug && old_eps != eps)
                std::cout << "VERITAS DEBUG eps increase " << old_eps << " -> "
                    << eps
                    << " (upper " << std::get<1>(current_bounds())
                    << ", step " << num_steps
                    << ", avg_t " << avg_eps_update_time_
                    << ")"
                    << std::endl;
        }

        void maybe_decrease_eps_()
        {
            if (!auto_eps) return;

            double t = time_since_start();
            double time_since_previous_update = t - last_eps_update_time_;

            if (last_eps_update_time_ > 0.0 && time_since_previous_update
                    > 2*avg_eps_update_time_)
            {
                avg_eps_update_time_ = 0.2 * avg_eps_update_time_ +
                    0.8*time_since_previous_update;
                eps_increment_ = std::max(0.01, eps_increment_/2.0);
                FloatT old_eps = eps;
                eps = std::max<FloatT>(0.5, eps-eps_increment_);

                if (debug && old_eps != eps)
                    std::cout << "VERITAS DEBUG eps decrease " << old_eps
                        << " -> " << eps
                        << " (upper " << std::get<1>(current_bounds())
                        << ", step " << num_steps
                        << ", avg_t " << avg_eps_update_time_
                        << ")"
                        << std::endl;
            }
        }


    }; // class Search

    inline std::ostream&
    operator<<(std::ostream& strm, const Solution& sol)
    {
        return strm << "Solution {output=" << sol.output << '}';
    }


} // namespace veritas

#include "heuristics.hpp"

namespace veritas {

    inline
    std::shared_ptr<VSearch>
    VSearch::max_output(const AddTree& at)
    {
        return std::unique_ptr<VSearch>(new Search<MaxOutputHeuristic>(at));
    }

    inline
    std::shared_ptr<VSearch>
    VSearch::min_dist_to_example(const AddTree& at,
            const std::vector<FloatT>& example, FloatT output_threshold)
    {
        return std::unique_ptr<VSearch>(new Search<MinDistToExampleHeuristic>(
                    at, example, output_threshold));
    }

} // namespace veritas

#endif // VERITAS_SEARCH_HPP
